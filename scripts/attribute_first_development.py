"""Post-hoc attribution of frozen Nautilus fills; no new trades/model/OOS access."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/first_development/v20261121_001"
SOURCE = BASE / "results_v003/lightgbm_validation/slippage_5bps"
OUT = BASE / "attribution_v001"
HOUR_NS = 3_600_000_000_000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fee_sides(quantity, delta):
    """Allocate a reversal's fee to closed and opened quantities."""
    if quantity * delta < 0:
        closing = min(abs(quantity), abs(delta))
        parts = [("long" if quantity > 0 else "short", closing / abs(delta))]
        if abs(delta) > closing:
            parts.append(("long" if delta > 0 else "short", 1 - closing / abs(delta)))
        return parts
    return [("long" if delta > 0 else "short", 1.)]


def main():
    inputs = [SOURCE / n for n in ("daily.csv", "fills.csv", "funding.csv")]
    inputs.append(BASE / "prepared_v003/mark.parquet")
    inputs.append(BASE / "prepared_v003/trade.parquet")
    inputs.append(SOURCE / "monthly_returns.csv")
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    daily, fills, funding = [pd.read_csv(p) for p in inputs[:3]]
    stamps = pd.DatetimeIndex(pd.to_datetime(daily.timestamp, utc=True)).asi8
    marks = {}
    trades = pd.read_parquet(inputs[4])
    trade_lookup = {(r.instrument_id, int(r.bar_open_ms)): float(r.quote_volume / r.volume)
                    for r in trades.itertuples() if r.volume > 0}
    for symbol, group in pd.read_parquet(inputs[3]).groupby("instrument_id"):
        group = group.sort_values("bar_open_ms")
        marks[symbol] = (group.bar_open_ms.to_numpy(np.int64) * 1_000_000 + HOUR_NS,
                         group.close.to_numpy(float))

    def mark(symbol, stamp):
        times, values = marks[symbol]
        ix = int(np.searchsorted(times, stamp, side="right")) - 1
        if ix < 0 or stamp - times[ix] > 2 * HOUR_NS:
            raise ValueError(f"Unavailable/stale mark: {symbol}/{stamp}")
        return round(float(values[ix]), 8)

    # No rerun of trading decisions: reconstruct only fixed linear cash flows.
    events = defaultdict(list)
    for r in fills.itertuples():
        events[r.instrument_id].append((int(r.timestamp_ns), 0, r))
    for r in funding.itertuples():
        events[r.instrument_id].append((int(r.timestamp_ns), 1, r))
    rows = []
    max_quantity_error = 0.
    for symbol, records in sorted(events.items()):
        records.sort(key=lambda x: (x[0], x[1]))
        pos = 0.
        cursor = 0
        previous_price = None
        for i, stamp in enumerate(stamps):
            parts = {side: {"price_pnl": 0., "funding": 0., "fees": 0.,
                            "slippage_proxy": 0., "traded_notional": 0.} for side in ("long", "short")}
            while cursor < len(records) and records[cursor][0] <= stamp:
                event_stamp, kind, r = records[cursor]
                if event_stamp < stamps[0]:
                    raise ValueError("Unexpected pre-start position")
                if kind == 0:
                    if pos:
                        parts["long" if pos > 0 else "short"]["price_pnl"] += (
                            pos * (r.price - previous_price))
                    delta = r.quantity * (1 if r.side == "BUY" else -1)
                    vwap = trade_lookup[(symbol, event_stamp // 1_000_000 - 3_600_000)]
                    expected_fill = round(vwap * (1.0005 if delta > 0 else .9995), 8)
                    if abs(expected_fill - r.price) > 1.1e-8:
                        raise ValueError("Fill does not match registered VWAP/slippage proxy")
                    slip = delta * (r.price - vwap)
                    for side, fraction in fee_sides(pos, delta):
                        parts[side]["fees"] += r.commission_usdt * fraction
                        parts[side]["slippage_proxy"] += slip * fraction
                        parts[side]["traded_notional"] += r.notional_usdt * fraction
                    pos += delta
                    if abs(pos) < 1e-9:
                        pos = 0.
                    previous_price = r.price
                else:
                    error = abs(pos - r.signed_quantity)
                    max_quantity_error = max(max_quantity_error, error)
                    if error > 1e-6 or pos == 0:
                        raise ValueError(f"Funding position mismatch: {symbol}/{event_stamp}")
                    parts["long" if pos > 0 else "short"]["funding"] += r.cashflow_usdt
                cursor += 1
            end_mark = mark(symbol, int(stamp)) if pos else previous_price
            if pos:
                parts["long" if pos > 0 else "short"]["price_pnl"] += pos * (end_mark - previous_price)
            previous_price = end_mark
            for side, values in parts.items():
                if any(values.values()):
                    rows.append({"timestamp": daily.timestamp.iloc[i], "instrument_id": symbol,
                                 "side": side, **values,
                                 "net_pnl": values["price_pnl"] + values["funding"] - values["fees"]})
        if cursor != len(records) or abs(pos) > 1e-9:
            raise ValueError("Unconsumed events or non-flat final position")
    detail = pd.DataFrame(rows)
    detail["price_pnl_before_slippage"] = detail.price_pnl + detail.slippage_proxy
    numeric = ["price_pnl", "price_pnl_before_slippage", "funding", "fees", "slippage_proxy",
               "traded_notional", "net_pnl"]
    totals = detail.groupby("timestamp")[numeric].sum().reindex(daily.timestamp, fill_value=0.)
    expected = daily.strategy_nav.diff().fillna(daily.strategy_nav.iloc[0] - 100000).to_numpy()
    residual = totals.net_pnl.to_numpy() - expected
    if abs(residual).max() > .01 or abs(residual.cumsum()).max() > .01:
        raise ValueError(f"NAV attribution mismatch: {abs(residual).max()}/{abs(residual.cumsum()).max()}")
    for col, ledger in [("fees", "commissions_usdt"), ("funding", "funding_cashflow_usdt"),
                        ("traded_notional", "traded_notional_usdt")]:
        if not np.allclose(totals[col], daily[ledger], rtol=0, atol=.001):
            raise ValueError(f"Daily {col} ledger mismatch")
    OUT.mkdir(parents=True, exist_ok=True)
    detail["month"] = detail.timestamp.str[:7]
    dates = pd.to_datetime(detail.timestamp, utc=True).dt.tz_localize(None) - pd.Timedelta(1, "ns")
    detail["holding_week_start"] = dates.dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    # Dollar contributions are additive; percentages below use actual month-start NAV.
    for name, keys in [("monthly_side", ["month", "side"]),
                       ("monthly_asset_side", ["month", "instrument_id", "side"]),
                       ("weekly_side", ["holding_week_start", "side"]),
                       ("annual_asset_side", ["instrument_id", "side"])]:
        detail.groupby(keys)[numeric].sum().reset_index().to_csv(OUT / f"{name}.csv", index=False)
    detail.to_csv(OUT / "daily_asset_side.csv", index=False)
    monthly = detail.groupby("month")[numeric].sum()
    month_returns = pd.read_csv(SOURCE / "monthly_returns.csv").iloc[:, :2]
    return_map = dict(zip(month_returns.iloc[:, 0].str[:7], month_returns.iloc[:, 1], strict=True))
    monthly["reported_return"] = pd.Series(return_map)
    # First value of a month is already an end-of-interval snapshot; use prior row.
    first_indices = daily.groupby(daily.timestamp.str[:7]).head(1).index
    start_nav = pd.Series({daily.timestamp.iloc[i][:7]: daily.strategy_nav.iloc[i-1] if i else 100000.
                           for i in first_indices})
    monthly["start_nav"] = start_nav
    for col in ("price_pnl", "funding", "fees", "net_pnl"):
        monthly[f"{col}_over_start_nav"] = monthly[col] / monthly.start_nav
    if set(monthly.index) != set(return_map) or not np.allclose(
            monthly.net_pnl_over_start_nav, monthly.reported_return, rtol=0, atol=1e-8):
        raise ValueError("Monthly attribution does not match original report boundaries")
    monthly.to_csv(OUT / "monthly_components.csv")
    daily_out = daily.copy()
    daily_out["attributed_pnl"] = totals.net_pnl.to_numpy()
    daily_out["residual_usdt"] = residual
    daily_out.to_csv(OUT / "daily_reconciliation.csv", index=False)
    jun = detail[detail.month == "2022-06"]
    jun.groupby(["holding_week_start", "side"])[numeric].sum().to_csv(OUT / "june_weekly_side.csv")
    jun.groupby(["holding_week_start", "instrument_id", "side"])[numeric].sum().to_csv(
        OUT / "june_weekly_asset_side.csv")
    top = jun.groupby("instrument_id")[numeric].sum().sort_values("net_pnl", ascending=False)
    top.to_csv(OUT / "june_asset_contributions.csv")
    side = detail.groupby("side")[numeric].sum()
    side.to_csv(OUT / "annual_side.csv")
    report = {"success": True, "post_hoc_descriptive_analysis": True,
              "OOS_performance_inspected": False, "strategy_changed": False,
              "daily_max_residual_usdt": float(abs(residual).max()),
              "cumulative_max_residual_usdt": float(abs(residual.cumsum()).max()),
              "funding_quantity_max_error": max_quantity_error,
              "annual": side[numeric].sum().to_dict(), "annual_side": side.to_dict("index"),
              "june_side": jun.groupby("side")[numeric].sum().to_dict("index"),
              "june_top_assets": top.head(10).reset_index().to_dict("records"),
              "other_months_cash_pnl": detail[detail.month != "2022-06"][numeric].sum().to_dict(),
              "other_months_compounded_return": float(np.prod([1+v for k, v in return_map.items()
                                                               if k != "2022-06"]) - 1),
              "input_hashes": hashes,
              "boundary_note": "Month of original 00:00 UTC NAV timestamp; not civil-day intraday attribution.",
              "method_note": "Actual-fill linear marked PnL; side is held position sign, reversal fees split by quantity.",
              "slippage_note": "Fixed actual quantities versus same source VWAP, not a zero-cost resimulation or arrival-mid estimate."}
    if any(sha(ROOT / name) != digest for name, digest in hashes.items()):
        raise ValueError("Inputs changed during attribution")
    (OUT / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    plot_attribution(detail, monthly, top)
    print(json.dumps({k: v for k, v in report.items() if k not in ("input_hashes", "june_top_assets")}, indent=2))


def plot_attribution(detail, monthly, top):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(12, 12), constrained_layout=True)
    sides = detail.groupby(["month", "side"]).net_pnl.sum().unstack().reindex(monthly.index)
    x = np.arange(len(sides))
    for i, side in enumerate(("long", "short")):
        axes[0].bar(x + (i - .5) * .36, sides[side], width=.36, label=side.title())
    axes[0].set_xticks(x, [m[-2:] for m in sides.index])
    axes[0].set_title("2022 monthly net cash PnL by held side")
    axes[0].legend()
    daily = detail.groupby(["timestamp", "side"]).net_pnl.sum().unstack().fillna(0).cumsum()
    for side in ("long", "short"):
        axes[1].plot(pd.to_datetime(daily.index), daily[side], label=side.title())
    axes[1].set_title("Cumulative net cash contributions (not standalone portfolio returns)")
    axes[1].legend()
    chosen = pd.concat([top.head(5), top.tail(5)]).sort_values("net_pnl")
    axes[2].barh(chosen.index, chosen.net_pnl,
                 color=["#21918c" if v > 0 else "#c44e52" for v in chosen.net_pnl])
    axes[2].set_title("June: five largest positive and negative asset contributions")
    axes[2].set_xlabel("USDT")
    for ax in axes:
        ax.grid(alpha=.2)
        if ax is not axes[2]:
            ax.set_ylabel("USDT")
            ax.axhline(0, color="black", lw=.7)
    path = ROOT / "reports/figures/first_development/profit_attribution.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
