"""Rebuild corrected2022 inputs from verified caches; preserve2021 training values."""

from __future__ import annotations

import json
import math
import shutil
from datetime import date, timedelta

import pandas as pd
from audit_development_continuity import sha
from development_continuity_rules import mondays, normalized, numeric_history
from prepare_first_development import DAY, FEATURES, HOUR, OUTPUT, ROOT, funding_feature, load_daily

DESTINATION = OUTPUT.parent / "prepared_v003"
RECOVERY = OUTPUT.parent / "trade_recovery"


def run():
    original = json.loads((OUTPUT / "manifest.json").read_text())
    if any(sha(OUTPUT / name) != digest for name, digest in original["output_hashes"].items()):
        raise ValueError("Original prepared cache changed")
    recovered = json.loads((RECOVERY / "summary.json").read_text())
    if not recovered["success"] or recovered["recovered_hours"] != 1440 or sha(RECOVERY / "trade_overlay.parquet") != recovered["overlay_sha256"]:
        raise ValueError("Verified complete trade repair required")
    if (DESTINATION / "manifest.json").exists():
        result = json.loads((DESTINATION / "manifest.json").read_text())
        if result["contract"]["script_sha256"] != sha(ROOT / "scripts/integrate_first_development_trades.py"):
            raise ValueError("Integration code changed:choose new version")
        if any(sha(DESTINATION / name) != digest for name, digest in result["output_hashes"].items()):
            raise ValueError("Integrated cache changed")
        print("Verified existing integrated cache", flush=True)
        return
    trades = pd.read_parquet(OUTPUT / "trade.parquet")
    overlay = pd.read_parquet(RECOVERY / "trade_overlay.parquet")
    old_keys = set(zip(trades.instrument_id, trades.bar_open_ms, strict=True))
    if any((r.instrument_id, r.bar_open_ms) in old_keys for r in overlay.itertuples()):
        raise ValueError("Trade overlay replaces original keys")
    merged = pd.concat([trades, overlay[list(trades.columns)]], ignore_index=True).sort_values(["instrument_id", "bar_open_ms"])
    marks = pd.read_parquet(OUTPUT / "mark.parquet")
    funding = pd.read_parquet(OUTPUT / "funding.parquet")
    daily_rows, features, bindings = [], [], {}
    for symbol in original["symbols"]:
        early, _ = load_daily(symbol, True, bindings)
        later, _ = load_daily(symbol, False, bindings)
        corrected = overlay[overlay.instrument_id == symbol].copy()
        corrected["day"] = pd.to_datetime(corrected.bar_open_ms, unit="ms", utc=True).dt.strftime("%Y-%m-%d")
        corrections = {d: g.sort_values("bar_open_ms") for d, g in corrected.groupby("day")}
        for row in later:
            group = corrections.get(row["data_day"])
            if group is None:
                continue
            if len(group) != 24:
                raise ValueError("Expected complete recovered trade day")
            row.update(trade_hours=24, trade_close=float(group.close.iloc[-1]),
                       trade_volume_sum=float(group.volume.sum()),
                       trade_quote_volume_sum=float(group.quote_volume.sum()),
                       taker_buy_quote_volume_sum=float(group.taker_buy_quote_volume.sum()),
                       imbalance_inputs_valid=True)
            row["trade_close_valid_for_history"] = bool(
                row["trade_volume_sum"] > 0 and row["trade_close"] > 0
                and row["episode_number"] == row["close_episode_number"]
                and not row["known_lifecycle_order_block"])
            row["base_failure_mask"] &= ~(1 | 4)
        points = [normalized(r, True) for r in early] + [normalized(r) for r in later]
        history = numeric_history(points)
        normalized_days = {p["day"]: p for p in points}
        rows = {date.fromisoformat(r["data_day"]): r for r in early + later}
        symbol_marks = marks[marks.instrument_id == symbol]
        mark_counts = (symbol_marks.bar_open_ms // DAY).value_counts().to_dict()
        trade_lookup = {int(r.bar_open_ms): (float(r.volume), float(r.quote_volume))
                        for r in merged[merged.instrument_id == symbol].itertuples()}
        events = funding[funding.instrument_id == symbol].sort_values("event_timestamp_ms")
        events = events.drop(columns="instrument_id").to_dict("records")
        for day, row in rows.items():
            daily_rows.append({"instrument_id": symbol, "data_day": day.isoformat(),
                               "history_closes": history[day], "trade_close": row["trade_close"]})
        for decision in mondays():
            cutoff = int(pd.Timestamp(decision, tz="UTC").timestamp() * 1000)
            day = decision - timedelta(days=1)
            row = rows[day]
            recent = [rows.get(day - timedelta(days=i)) for i in range(7)]
            imbalance_valid = all(recent) and all(normalized_days[day - timedelta(days=i)]["imbalance"] for i in range(7))
            rate = funding_feature(events, cutoff)
            if not (history[day] >= 121 and mark_counts.get((cutoff - DAY) // DAY, 0) == 24
                    and imbalance_valid and (row["base_failure_mask"] & ~(8 | 2)) == 0 and rate is not None):
                continue
            quote = math.fsum(r["trade_quote_volume_sum"] for r in recent)
            buy = math.fsum(r["taker_buy_quote_volume_sum"] for r in recent)
            if quote <= 0:
                continue
            entry, exit_row = trade_lookup.get(cutoff + HOUR), trade_lookup.get(cutoff + HOUR + 7 * DAY)
            label = None
            if entry and exit_row and entry[0] > 0 and exit_row[0] > 0:
                label = (exit_row[1] / exit_row[0]) / (entry[1] / entry[0]) - 1
            item = {"instrument_id": symbol, "decision_date": decision.isoformat(),
                    "feature_cutoff_ms": cutoff, "decision_ms": cutoff + HOUR,
                    "label_available_ms": cutoff + 3 * HOUR + 7 * DAY,
                    "label": label, "funding7": rate, "imbalance7": 2 * buy / quote - 1}
            for horizon in (20, 60, 120):
                item[f"momentum{horizon}"] = row["trade_close"] / rows[day - timedelta(days=horizon)]["trade_close"] - 1
            if not all(math.isfinite(item[k]) for k in FEATURES):
                raise ValueError("Nonfinite corrected feature")
            features.append(item)
    old_features = pd.read_parquet(OUTPUT / "features.parquet")
    new_features = pd.DataFrame(features)
    sort = ["decision_date", "instrument_id"]
    pd.testing.assert_frame_equal(
        old_features[old_features.feature_cutoff_ms < 1640995200000].sort_values(sort).reset_index(drop=True),
        new_features[new_features.feature_cutoff_ms < 1640995200000][old_features.columns].sort_values(sort).reset_index(drop=True),
        check_dtype=False, check_exact=True)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(DESTINATION / "trade.parquet", index=False)
    new_features.to_parquet(DESTINATION / "features.parquet", index=False)
    pd.DataFrame(daily_rows).to_parquet(DESTINATION / "daily.parquet", index=False)
    for name in ("mark.parquet", "funding.parquet"):
        shutil.copyfile(OUTPUT / name, DESTINATION / name)
    (DESTINATION / "source_bindings.json").write_text(json.dumps({
        "original_prepared_manifest": sha(OUTPUT / "manifest.json"),
        "trade_recovery_manifest": sha(RECOVERY / "summary.json"), "daily": bindings}, indent=2))
    report = {**original, "contract": {"script_sha256": sha(ROOT / "scripts/integrate_first_development_trades.py"),
               "original_prepared_sha256": sha(OUTPUT / "manifest.json"), "trade_overlay_sha256": recovered["overlay_sha256"]},
              "feature_rows": len(features), "training_2021_exactly_unchanged": True,
              "recovered_trade_hours_integrated": 1440,
              "output_hashes": {p.name: sha(p) for p in DESTINATION.iterdir() if p.name != "manifest.json"}}
    (DESTINATION / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"success": True, "feature_rows": len(features),
                      "training_2021_exactly_unchanged": True, "trade_overlay_hours": 1440}), flush=True)


if __name__ == "__main__":
    run()
