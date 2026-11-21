"""Integrated, conditional research panel for registered Experiment005."""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from audit_development_continuity import DEV_COLUMNS, EARLY_COLUMNS, sha
from development_continuity_rules import mondays, normalized, numeric_history

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT.parents[1] / "data/canonical"
DAILY = CANONICAL / "binance_um_daily_research/v20261118_001"
EARLY = CANONICAL / "binance_um_early_research/v20261119_001"
HOURLY = CANONICAL / "binance_um_research/v20261117_001"
RECOVERY = CANONICAL / "binance_um_development_mark_recovery/v20261121_001"
OUTPUT = ROOT / "data/interim/first_development/v20261121_001/prepared"
FEATURES = ["momentum20", "momentum60", "momentum120", "funding7", "imbalance7"]
DAY = 86400000
HOUR = 3600000
START = 1609459200000
END = 1672531200000


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_daily(symbol, early, bindings):
    root = EARLY if early else DAILY
    index_path = root / "index" / f"{symbol}.json"
    index = json.loads(index_path.read_text())
    path = root / "daily" / f"{symbol}.parquet"
    if sha(path) != index["daily_sha256"]:
        raise ValueError(f"Daily source changed:{symbol}")
    bindings[f"daily/{early}/{symbol}"] = {"index": sha(index_path), "daily": sha(path)}
    columns = list(set((EARLY_COLUMNS if early else DEV_COLUMNS) + [
        "trade_quote_volume_sum", "taker_buy_quote_volume_sum", "trade_volume_sum"]))
    rows = pq.read_table(path, columns=columns, filters=[
        ("data_day", ">=", "2020-08-01" if early else "2021-01-01"),
        ("data_day", "<", "2021-01-01" if early else "2023-01-01")]).to_pylist()
    return rows, index


def load_hours(symbol, kind, month, index, early, bindings):
    root = EARLY if early else HOURLY
    relative = f"observations/{kind}/{symbol}/{month}.parquet"
    path = root / relative
    if early:
        record = next((p for p in index["partitions"] if p["relative_path"] == relative), None)
    else:
        part = {"trade": "klines", "mark": "markPriceKlines", "funding": "fundingRate"}[kind]
        tail = f"fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip" if kind == "funding" else (
            f"{part}/{symbol}/1h/{symbol}-1h-{month}.zip")
        record = index["sources"].get("data/futures/um/monthly/" + tail)
    if record is None:
        if path.exists():
            raise ValueError("Unbound hourly source")
        return []
    expected = record["parquet_sha256"]
    if not path.exists() or sha(path) != expected:
        raise ValueError(f"Hourly source changed:{relative}")
    bindings[f"hourly/{early}/{relative}"] = expected
    if kind == "funding":
        cols = ["event_timestamp_ms", "funding_rate", "funding_interval_hours"]
    elif kind == "mark":
        cols = ["bar_open_ms", "close"]
    else:
        cols = ["bar_open_ms", "close", "volume", "quote_volume"]
    return pq.read_table(path, columns=cols).to_pylist()


def funding_feature(events, cutoff):
    selected = [r for r in events if cutoff - 7 * DAY <= r["event_timestamp_ms"]
                and r["event_timestamp_ms"] + HOUR < cutoff]
    if not selected:
        return None
    intervals = [r["funding_interval_hours"] for r in selected]
    if any(v is None or v <= 0 for v in intervals) or sum(intervals) < 168:
        return None
    last = selected[-1]
    if cutoff - last["event_timestamp_ms"] > last["funding_interval_hours"] * HOUR + 1000:
        return None
    if any(b["event_timestamp_ms"] - a["event_timestamp_ms"]
           > max(a["funding_interval_hours"], b["funding_interval_hours"]) * HOUR + 1000
           for a, b in zip(selected, selected[1:], strict=False)):
        return None
    rates = [r["funding_rate"] for r in selected]
    return math.fsum(rates) if all(math.isfinite(v) for v in rates) else None


def prepare(output):
    started = time.monotonic()
    identity_path = ROOT / "data/interim/early_weekly_universe/v20261120_001/asset_review.json"
    identities = json.loads(identity_path.read_text())
    symbols = sorted(r["instrument_id"] for r in identities
                     if r["identity_status"] == "corroborated_identity"
                     and r["instrument_id"] not in {"BCHUSDT", "KNCUSDT", "LENDUSDT"})
    if len(symbols) != 37:
        raise ValueError("Registered fixed cohort changed")
    contract = {"script_sha256": sha(Path(__file__)), "identity_sha256": sha(identity_path),
                "rules_sha256": sha(ROOT / "scripts/development_continuity_rules.py"),
                "registration_sha256": sha(ROOT / "experiments/005_first_historical_development_run.md"),
                "overlay_sha256": sha(RECOVERY / "mark_gap_overlay.parquet"), "symbols": symbols}
    if (output / "manifest.json").exists():
        old = json.loads((output / "manifest.json").read_text())
        if old["contract"] != contract:
            raise ValueError("Prepared version bound to different code/inputs; choose new --output")
        if any(sha(output / name) != digest for name, digest in old["output_hashes"].items()):
            raise ValueError("Prepared outputs changed")
        print(json.dumps({"success": True, "cache_hit": True, "output": str(output)}))
        return
    recovery_manifest = json.loads((RECOVERY / "manifest.json").read_text())
    if not recovery_manifest["recovery_complete"] or contract["overlay_sha256"] != recovery_manifest["overlay_sha256"]:
        raise ValueError("Verified complete overlay required")
    overlays = pq.read_table(RECOVERY / "mark_gap_overlay.parquet",
                             columns=["instrument_id", "bar_open_ms", "close"]).to_pylist()
    bindings, all_daily, all_trade, all_marks, all_funding, features = {}, [], [], [], [], []
    for position, symbol in enumerate(symbols, 1):
        early, early_index = load_daily(symbol, True, bindings)
        later, index = load_daily(symbol, False, bindings)
        points = [normalized(r, True) for r in early] + [normalized(r) for r in later]
        history = numeric_history(points)
        normalized_days = {p["day"]: p for p in points}
        daily_rows = {date.fromisoformat(r["data_day"]): r for r in early + later}
        trades, marks, funding = [], [], []
        for kind, target in [("trade", trades), ("mark", marks), ("funding", funding)]:
            if kind != "trade":
                target += load_hours(symbol, kind, "2020-12", early_index, True, bindings)
            for year in (2021, 2022):
                for month in range(1, 13):
                    target += load_hours(symbol, kind, f"{year}-{month:02d}", index, False, bindings)
        marks = {r["bar_open_ms"]: r["close"] for r in marks}
        for row in overlays:
            if row["instrument_id"] == symbol:
                if row["bar_open_ms"] in marks:
                    raise ValueError("Overlay attempts to overwrite original mark")
                marks[row["bar_open_ms"]] = row["close"]
        trade_lookup = {r["bar_open_ms"]: r for r in trades}
        if len(trade_lookup) != len(trades):
            raise ValueError("Duplicate trade keys")
        funding.sort(key=lambda r: r["event_timestamp_ms"])
        if len({r["event_timestamp_ms"] for r in funding}) != len(funding):
            raise ValueError("Duplicate funding events")
        for day, row in daily_rows.items():
            all_daily.append({"instrument_id": symbol, "data_day": day.isoformat(),
                              "history_closes": history[day], "trade_close": row["trade_close"]})
        for decision in mondays():
            cutoff = int(pd.Timestamp(decision, tz="UTC").timestamp() * 1000)
            day = decision - timedelta(days=1)
            row = daily_rows[day]
            recent = [daily_rows.get(day - timedelta(days=i)) for i in range(7)]
            valid_imbalance = all(recent) and all(normalized_days[day - timedelta(days=i)]["imbalance"] for i in range(7))
            mark_hours = sum(cutoff - DAY <= t < cutoff for t in marks)
            funding7 = funding_feature(funding, cutoff)
            valid = (history[day] >= 121 and mark_hours == 24 and valid_imbalance
                     and (row["base_failure_mask"] & ~(8 | 2)) == 0 and funding7 is not None)
            if not valid:
                continue
            quote = math.fsum(r["trade_quote_volume_sum"] for r in recent)
            buy = math.fsum(r["taker_buy_quote_volume_sum"] for r in recent)
            if quote <= 0:
                continue
            entry_ms = cutoff + HOUR
            exit_ms = entry_ms + 7 * DAY
            entry, exit_row = trade_lookup.get(entry_ms), trade_lookup.get(exit_ms)
            label = None
            if entry and exit_row and entry["volume"] > 0 and exit_row["volume"] > 0:
                label = (exit_row["quote_volume"] / exit_row["volume"]) / (entry["quote_volume"] / entry["volume"]) - 1
            item = {"instrument_id": symbol, "decision_date": decision.isoformat(),
                    "feature_cutoff_ms": cutoff, "decision_ms": cutoff + HOUR,
                    "label_available_ms": exit_ms + 2 * HOUR,
                    "label": label, "funding7": funding7, "imbalance7": 2 * buy / quote - 1}
            for horizon in (20, 60, 120):
                item[f"momentum{horizon}"] = row["trade_close"] / daily_rows[day - timedelta(days=horizon)]["trade_close"] - 1
            if not all(math.isfinite(item[k]) for k in FEATURES):
                raise ValueError("Nonfinite feature")
            features.append(item)
        all_trade += [{"instrument_id": symbol, **r} for r in trades]
        all_marks += [{"instrument_id": symbol, "bar_open_ms": t, "close": p}
                      for t, p in sorted(marks.items())]
        all_funding += [{"instrument_id": symbol, **r} for r in funding]
        print(f"prepared {position}/{len(symbols)} {symbol}", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    products = {"daily": all_daily, "trade": all_trade, "mark": all_marks,
                "funding": all_funding, "features": features}
    for name, rows in products.items():
        pq.write_table(pa.Table.from_pylist(rows), output / f"{name}.parquet", compression="zstd")
    write(output / "source_bindings.json", bindings)
    counts = pd.DataFrame(features).groupby("decision_date").size()
    report = {"success": True, "contract": contract, "symbols": symbols,
              "feature_rows": len(features), "weekly_candidate_min": int(counts.min()),
              "weekly_candidate_max": int(counts.max()), "weekly_candidate_median": float(counts.median()),
              "certified_point_in_time_universe": False, "conditional_identity_bridge": True,
              "labels_computed": True, "model_fitted": False, "PnL_computed": False,
              "OOS_performance_inspected": False, "elapsed_seconds": time.monotonic() - started,
              "output_hashes": {p.name: sha(p) for p in output.iterdir() if p.is_file() and p.name != "manifest.json"}}
    write(output / "manifest.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("contract", "output_hashes", "symbols")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    prepare(parser.parse_args().output)
