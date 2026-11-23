"""Independent fills/funding/source-price and marked-NAV reconstruction."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DAY, HOUR, load_json, sha
from .repair import write_json
from .window_data import ms


def read_ledger(path, name):
    try:
        return pd.read_csv(path / (name + ".csv"))
    except pd.errors.EmptyDataError:
        return pd.DataFrame(
            columns={
                "fills": [
                    "timestamp_ns",
                    "instrument_id",
                    "side",
                    "quantity",
                    "price",
                    "commission_usdt",
                    "notional_usdt",
                ],
                "funding": [
                    "timestamp_ns",
                    "instrument_id",
                    "signed_quantity",
                    "cashflow_usdt",
                    "rate",
                    "mark_proxy",
                    "mark_available_ms",
                ],
            }[name]
        )


def apply_fill(position, delta, price):
    quantity, average = position
    realized = 0.0
    if not quantity or quantity * delta > 0:
        updated = quantity + delta
        average = (abs(quantity) * average + abs(delta) * price) / abs(updated)
    else:
        closed = min(abs(quantity), abs(delta))
        realized = closed * (price - average) * (1 if quantity > 0 else -1)
        updated = quantity + delta
        if abs(updated) < 1e-7:
            updated, average = 0.0, 0.0
        elif updated * quantity < 0:
            average = price
    return (updated, average), realized


class Oracle:
    def __init__(self, path, cases):
        self.marks = {}
        market = pd.read_parquet(
            path / "mark.parquet", columns=["instrument_id", "bar_open_ms", "close"]
        )
        for symbol, g in market.groupby("instrument_id"):
            self.marks[symbol] = (
                g.bar_open_ms.to_numpy(dtype=np.int64) + HOUR,
                g.close.to_numpy(float),
            )
        wanted = set()
        for case in cases:
            folder = path / "results" / f"{case['case']}_{case['bps']}bps"
            fills = read_ledger(folder, "fills")
            wanted.update(int(t) // 1000000 - HOUR for t in fills.timestamp_ns)
        trades = pd.read_parquet(
            path / "trade.parquet",
            columns=["instrument_id", "bar_open_ms", "volume", "quote_volume"],
        )
        trades = trades[trades.bar_open_ms.isin(wanted)]
        self.trades = {
            (row.instrument_id, int(row.bar_open_ms)): (float(row.volume), float(row.quote_volume))
            for row in trades.itertuples()
        }
        recovery = path / "recovered_bars.jsonl"
        if recovery.exists():
            for line in recovery.read_text().splitlines():
                value = json.loads(line)
                row = value["row"]
                symbol = value["symbol"]
                t = int(row["bar_open_ms"])
                if value["kind"] == "trade":
                    self.trades[(symbol, t)] = (row["volume"], row["quote_volume"])
                else:
                    stamps, prices = self.marks.get(
                        symbol, (np.array([], dtype=np.int64), np.array([], float))
                    )
                    order = np.argsort(np.r_[stamps, t + HOUR])
                    self.marks[symbol] = (
                        np.r_[stamps, t + HOUR][order],
                        np.r_[prices, row["close"]][order],
                    )
        funding = pd.read_parquet(path / "funding.parquet")
        self.funding = {
            s: list(
                zip(g.event_timestamp_ms.astype("int64"), g.funding_rate.astype(float), strict=True)
            )
            for s, g in funding.groupby("instrument_id")
        }
        self.notices = load_json(path / "notices.json")

    def mark(self, symbol, t):
        stamps, prices = self.marks[symbol]
        i = int(np.searchsorted(stamps, t, side="right")) - 1
        if i < 0 or not 0 <= t - stamps[i] <= 2 * HOUR:
            raise ValueError("Independent held mark unavailable")
        return float(prices[i]), int(stamps[i])

    def add_mean_assumptions(self, config, path):
        """Independently verify the declared estimate against original adjacent rows."""
        target = path / "funding_assumptions.json"
        saved = load_json(target)
        gate = load_json(path / "preflight.json")
        if gate["source_bindings"].get(str(target.resolve())) != sha(target):
            raise ValueError("Unbound funding assumptions")
        original = path / "funding.parquet"
        if sha(original) != saved["original_funding_sha256"]:
            raise ValueError("Original funding changed after estimation")
        policy = config["funding_imputation"]
        start, stop = ms(policy["start_utc"]), ms(policy["stop_exclusive_utc"])
        if (
            policy["method"] != "adjacent_mean"
            or policy["use"] != "accounting_only"
            or saved["method"] != "adjacent_mean"
            or saved["uses_future_anchor"] is not True
            or saved["start_ms"] != start
            or saved["stop_exclusive_ms"] != stop
        ):
            raise ValueError("Funding assumption policy mismatch")
        records = saved["records"]
        if len(records) != saved["estimated_events"]:
            raise ValueError("Funding estimate count mismatch")
        if not records:
            return 0
        stamps = sorted({r[k] for r in records for k in ["before_ms", "after_ms"]})
        raw = pd.read_parquet(
            original,
            columns=[
                "instrument_id",
                "event_timestamp_ms",
                "funding_rate",
                "funding_interval_hours",
            ],
            filters=[("event_timestamp_ms", "in", stamps)],
        )
        anchors = {
            (r.instrument_id, int(r.event_timestamp_ms)): (
                float(r.funding_rate),
                float(r.funding_interval_hours),
            )
            for r in raw.itertuples()
        }
        by_symbol = {
            s: [int(t) for t, _ in self.funding[s]] for s in {r["symbol"] for r in records}
        }
        seen, groups = set(), {}
        for record in records:
            s, t, a, b = (record[k] for k in ["symbol", "timestamp_ms", "before_ms", "after_ms"])
            left, right = anchors[(s, a)], anchors[(s, b)]
            i = int(np.searchsorted(by_symbol[s], a))
            if (
                i + 1 >= len(by_symbol[s])
                or by_symbol[s][i] != a
                or by_symbol[s][i + 1] != b
                or not np.isfinite(left + right).all()
                or left[1] <= 0
                or left[1] != right[1]
                or record["interval_hours"] != left[1]
                or record["before_rate"] != left[0]
                or record["after_rate"] != right[0]
                or not np.isfinite(record["rate"])
                or abs(record["rate"] - (left[0] + right[0]) / 2) > 1e-15
                or not a < t < b
                or not start <= t < stop
                or (s, t) in seen
            ):
                raise ValueError("Independent mean-funding anchor/rate mismatch")
            seen.add((s, t))
            groups.setdefault((s, a, b, left[1]), set()).add(t)
        for (_s, a, b, hours), provided in groups.items():
            step, base = int(round(hours * HOUR)), a // HOUR * HOUR
            count = int(round((b - base) / step)) if step > 0 else 0
            expected = {base + i * step for i in range(1, count)}
            if (
                step <= 0
                or count <= 1
                or a - base > 1000
                or abs(b - (base + count * step)) > 1000
                or provided != expected
                or not all(start <= t < stop for t in expected)
            ):
                raise ValueError("Independent mean-funding schedule mismatch")
        for r in records:
            self.funding[r["symbol"]].append((r["timestamp_ms"], r["rate"]))
        for s in by_symbol:
            self.funding[s].sort()
        return len(records)

    def fill_price(self, symbol, t, last):
        matches = [
            notice
            for key, notice in self.notices.items()
            if notice.get("symbol", key) == symbol and t == notice["exit_ms"]
        ]
        if len(matches) > 1:
            raise ValueError("Ambiguous independent notice exit")
        if matches:
            return matches[0]["exit_vwap"]
        if t != last - HOUR and (t % DAY != 2 * HOUR):
            raise ValueError("Unregistered fill time")
        v, q = self.trades[(symbol, t - HOUR)]
        if v <= 0:
            raise ValueError("Independent VWAP unavailable")
        return q / v


def audit_case(path, case, oracle, start, last):
    folder = path / "results" / f"{case['case']}_{case['bps']}bps"
    fills, funding = read_ledger(folder, "fills"), read_ledger(folder, "funding")
    recorded = {(row.instrument_id, int(row.timestamp_ns)): row for row in funding.itertuples()}
    if len(recorded) != len(funding):
        raise ValueError("Duplicate recorded funding")
    for row in fills.itertuples():
        sign = 1 if row.side == "BUY" else -1
        proxy = oracle.fill_price(row.instrument_id, int(row.timestamp_ns) // 1000000, last)
        expected = round(proxy * (1 + sign * case["bps"] / 10000), 8)
        if (
            abs(row.price - expected) > 1.1e-8
            or abs(row.quantity * row.price * 0.0005 - row.commission_usdt) > 1.1e-6
        ):
            raise ValueError("Independent execution price/fee mismatch")
    matched = set()
    for symbol, events in oracle.funding.items():
        subset = fills[fills.instrument_id.eq(symbol)].sort_values("timestamp_ns")
        quantities = [
            (int(row.timestamp_ns), float(row.quantity) * (1 if row.side == "BUY" else -1))
            for row in subset.itertuples()
        ]
        cursor, position = 0, 0.0
        for t, rate in events:
            if not start <= t <= last:
                continue
            ns = int(t) * 1000000
            while cursor < len(quantities) and quantities[cursor][0] < ns:
                position += quantities[cursor][1]
                cursor += 1
            if abs(position) < 1e-7:
                position = 0.0
            key = symbol, ns
            if not position:
                if key in recorded:
                    raise ValueError("Funding recorded while independently flat")
                continue
            if key not in recorded:
                raise ValueError("Held funding event omitted")
            row = recorded[key]
            price, available = oracle.mark(symbol, int(t))
            if (
                abs(row.signed_quantity - position) > 1e-7
                or abs(row.rate - rate) > 1e-12
                or abs(row.mark_proxy - price) > 1e-8
                or row.mark_available_ms != available
                or abs(-position * price * rate - row.cashflow_usdt) > 1.1e-6
            ):
                raise ValueError("Independent funding quantity/source/amount mismatch")
            matched.add(key)
    if matched != set(recorded):
        raise ValueError("Unexpected recorded funding")
    events = []
    for row in fills.itertuples():
        events.append((int(row.timestamp_ns), 1, row))
    for row in funding.itertuples():
        events.append((int(row.timestamp_ns), 0, row))
    events.sort(key=lambda x: (x[0], x[1]))
    daily = pd.read_csv(folder / "engine_daily.csv")
    expected_dates = pd.date_range(
        pd.Timestamp(start, unit="ms", tz="UTC"), pd.Timestamp(last, unit="ms", tz="UTC"), freq="D"
    )
    if not pd.DatetimeIndex(pd.to_datetime(daily.timestamp, utc=True)).equals(expected_dates):
        raise ValueError("Daily calendar mismatch")
    positions = {}
    cash = 100000.0
    cursor = 0
    maximum = 0.0
    for row in daily.itertuples():
        t = int(pd.Timestamp(row.timestamp).timestamp() * 1000)
        while cursor < len(events) and events[cursor][0] <= t * 1000000 + 100:
            _, kind, event = events[cursor]
            if kind == 0:
                cash += float(event.cashflow_usdt)
            else:
                delta = event.quantity * (1 if event.side == "BUY" else -1)
                positions[event.instrument_id], realized = apply_fill(
                    positions.get(event.instrument_id, (0.0, 0.0)), delta, event.price
                )
                cash += realized - event.commission_usdt
            cursor += 1
        unrealized = 0.0
        for symbol, (quantity, average) in positions.items():
            if abs(quantity) < 1e-7:
                continue
            price, _ = oracle.mark(symbol, t)
            unrealized += quantity * (round(price, 8) - average)
        error = max(abs(cash - row.cash_usdt), abs(cash + unrealized - row.strategy_nav))
        maximum = max(maximum, error)
        if error > 0.01:
            raise ValueError(f"Independent NAV/cash mismatch:{row.timestamp}:{error}")
    result = {
        "success": True,
        "verified_fills": len(fills),
        "verified_held_funding": len(matched),
        "daily_snapshots": len(daily),
        "max_independent_nav_cash_error_usdt": maximum,
    }
    write_json(folder / "independent_audit.json", result)
    return result


def attribution(path):
    folder = path / "results/lightgbm_5bps"
    fills = read_ledger(folder, "fills")
    funding = read_ledger(folder, "funding")
    signed = np.where(fills.side.eq("BUY"), fills.quantity, -fills.quantity)
    fills["trading_cashflow"] = -signed * fills.price
    asset = fills.groupby("instrument_id").agg(
        trading_cashflow=("trading_cashflow", "sum"),
        commissions=("commission_usdt", "sum"),
        traded_notional=("notional_usdt", "sum"),
    )
    asset["funding"] = (
        funding.groupby("instrument_id").cashflow_usdt.sum().reindex(asset.index, fill_value=0)
    )
    asset["net_pnl_usdt"] = asset.trading_cashflow - asset.commissions + asset.funding
    ending = load_json(folder / "engine_summary.json")["ending_nav"] - 100000
    if abs(asset.net_pnl_usdt.sum() - ending) > 0.01:
        raise ValueError("Asset contribution reconciliation failed")
    sides = {
        "long": {"gross_realized": 0.0, "commissions": 0.0, "funding": 0.0},
        "short": {"gross_realized": 0.0, "commissions": 0.0, "funding": 0.0},
    }
    for _symbol, g in fills.groupby("instrument_id"):
        position = (0.0, 0.0)
        for row in g.sort_values("timestamp_ns").itertuples():
            delta = row.quantity * (1 if row.side == "BUY" else -1)
            old = position[0]
            closing = min(abs(old), abs(delta)) if old * delta < 0 else 0.0
            position, realized = apply_fill(position, delta, row.price)
            if closing:
                side = "long" if old > 0 else "short"
                sides[side]["gross_realized"] += realized
                sides[side]["commissions"] += row.commission_usdt * closing / abs(delta)
            if abs(delta) > closing:
                side = "long" if delta > 0 else "short"
                sides[side]["commissions"] += (
                    row.commission_usdt * (abs(delta) - closing) / abs(delta)
                )
    for row in funding.itertuples():
        sides["long" if row.signed_quantity > 0 else "short"]["funding"] += row.cashflow_usdt
    for value in sides.values():
        value["net_pnl_usdt"] = value["gross_realized"] - value["commissions"] + value["funding"]
    if abs(sum(v["net_pnl_usdt"] for v in sides.values()) - ending) > 0.01:
        raise ValueError("Side contribution reconciliation failed")
    return asset.sort_values("net_pnl_usdt", ascending=False), pd.DataFrame(sides).T


def audit_all(config, path):
    summary = load_json(path / "simulation_summary.json")
    oracle = Oracle(path, summary["cases"])
    estimated = oracle.add_mean_assumptions(config, path) if config.get("funding_imputation") else 0
    start, last = ms(config["start"]), ms(config["stop_exclusive"]) - DAY
    results = [audit_case(path, case, oracle, start, last) for case in summary["cases"]]
    result = {
        "success": all(x["success"] for x in results),
        "cases": len(results),
        "maximum_nav_cash_error_usdt": max(
            x["max_independent_nav_cash_error_usdt"] for x in results
        ),
        "audit_code_sha256": sha(Path(__file__)),
        "assumed_funding_events_verified": estimated,
    }
    write_json(path / "independent_audit_summary.json", result)
    return result
