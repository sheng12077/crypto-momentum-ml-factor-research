"""Audit every existing identifier; never promote diagnostic flags to trading eligibility.

Read-only against inputs. Outputs are overwritten only in the explicitly selected
report directory. No network access, source repair, labels, models or PnL.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REASONS = {
    "trade_day_incomplete": 1,
    "mark_day_incomplete": 2,
    "no_trade_activity": 4,
    "history120_incomplete_or_wrong_episode": 8,
    "funding_missing_or_wrong_episode": 16,
    "funding_outside_reported_interval": 32,
    "known_order_stop": 64,
    "partial_lifecycle_day": 128,
    "scoped_execution_block": 256,
    "known_equity_episode": 512,
    "imbalance_inputs_invalid": 4096,
}
COLUMNS = [
    "instrument_id",
    "data_day",
    "trade_hours",
    "mark_hours",
    "trade_volume_sum",
    "price_funding_data_candidate",
    "base_failure_mask",
    "episode_number",
    "known_equity_episode",
    "lifecycle_origin_unverified",
]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def audit(daily_root, cohort_manifest, output):
    manifest = json.loads((daily_root / "manifest.json").read_text())
    cohort = set(json.loads(cohort_manifest.read_text())["symbols"])
    files = sorted((daily_root / "daily").glob("*.parquet"))
    expected = int(manifest["identifiers"])
    if len(files) != expected or len({f.stem for f in files}) != expected:
        raise ValueError("Full input inventory does not reconcile to source manifest")
    rows, errors = [], []
    dates = None
    totals = {}
    for position, path in enumerate(files, 1):
        symbol = path.stem
        item = {
            "instrument_id": symbol,
            "in_old_fixed_cohort": symbol in cohort,
            "old_backtest_disposition": "used_by_fixed_prototype"
            if symbol in cohort
            else "never_considered_by_fixed_cohort",
            "input_verified": False,
            "new_trading_eligibility": "not_assessed_by_this_diagnostic",
        }
        try:
            index_path = daily_root / "index" / (symbol + ".json")
            index = json.loads(index_path.read_text())
            if index["instrument_id"] != symbol or digest(path) != index["daily_sha256"]:
                raise ValueError("Daily/index identity or checksum mismatch")
            frame = pq.read_table(path, columns=COLUMNS).to_pandas()
            if len(frame) != index["rows"] or set(frame.instrument_id) != {symbol}:
                raise ValueError("Input row/identifier mismatch")
            stamps = pd.DatetimeIndex(pd.to_datetime(frame.data_day, utc=True))
            if dates is None:
                dates = stamps
                totals = {
                    k: np.zeros(len(frame), dtype=np.int64)
                    for k in [
                        "positive_volume_identifiers",
                        "legacy_price_funding_candidates",
                        "legacy_candidates_inside_old_cohort",
                        "legacy_candidates_outside_old_cohort",
                    ]
                }
            if (
                not stamps.equals(dates)
                or not stamps.is_unique
                or not stamps.is_monotonic_increasing
            ):
                raise ValueError("Daily grid mismatch/duplicate/unordered dates")
            bars = frame.trade_hours.gt(0)
            positive = bars & frame.trade_volume_sum.fillna(0).gt(0)
            candidate = frame.price_funding_data_candidate.fillna(False).astype(bool)
            masks = frame.base_failure_mask.to_numpy(dtype=np.int64)
            counts = {
                name: int(((masks & bit) != 0)[positive.to_numpy()].sum())
                for name, bit in REASONS.items()
            }
            history = frame.loc[positive, "data_day"]
            item.update(
                {
                    "input_verified": True,
                    "rows": len(frame),
                    "days_with_trade_bars": int(bars.sum()),
                    "positive_volume_days": int(positive.sum()),
                    "first_positive_volume_day": history.iloc[0] if len(history) else None,
                    "last_positive_volume_day": history.iloc[-1] if len(history) else None,
                    "complete_trade_positive_days": int(
                        (positive & frame.trade_hours.eq(24)).sum()
                    ),
                    "incomplete_marks_on_positive_days": int(
                        (positive & frame.mark_hours.lt(24)).sum()
                    ),
                    "legacy_price_funding_candidate_days": int(candidate.sum()),
                    "legacy_price_funding_candidate_ever": bool(candidate.any()),
                    "known_episode_numbers": int(frame.episode_number.nunique()),
                    "known_equity_days": int(frame.known_equity_episode.sum()),
                    "lifecycle_origin_unverified_on_positive_days": int(
                        (positive & frame.lifecycle_origin_unverified).sum()
                    ),
                    "source_daily_sha256": index["daily_sha256"],
                    **{"legacy_flag_days_" + key: value for key, value in counts.items()},
                }
            )
            totals["positive_volume_identifiers"] += positive.to_numpy(dtype=np.int64)
            totals["legacy_price_funding_candidates"] += candidate.to_numpy(dtype=np.int64)
            totals[
                "legacy_candidates_inside_old_cohort"
                if symbol in cohort
                else "legacy_candidates_outside_old_cohort"
            ] += candidate.to_numpy(dtype=np.int64)
        except Exception as exc:
            item["error"] = str(exc)
            errors.append({"instrument_id": symbol, "error": str(exc)})
        rows.append(item)
        if position % 100 == 0:
            print(f"Coverage audit {position}/{expected}; errors={len(errors)}", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(rows)
    table.to_csv(output / "assets.csv", index=False)
    timeline = pd.DataFrame(totals, index=dates)
    timeline.index.name = "data_day_UTC"
    timeline.to_csv(output / "daily_diagnostic_counts.csv")
    prior = table.in_old_fixed_cohort
    eligible = (
        table.legacy_price_funding_candidate_ever.fillna(False).astype(bool)
        if "legacy_price_funding_candidate_ever" in table
        else pd.Series(False, index=table.index)
    )
    summary = {
        "success": not errors,
        "identifiers_expected": expected,
        "identifiers_accounted": len(table),
        "input_files_verified": int(table.input_verified.sum()),
        "old_fixed_cohort": int(prior.sum()),
        "outside_old_fixed_cohort": int((~prior).sum()),
        "legacy_price_funding_candidate_ever": int(eligible.sum()),
        "legacy_candidates_outside_old_cohort": int((eligible & ~prior).sum()),
        "positive_volume_identifiers": int(
            table.get("positive_volume_days", pd.Series(0, index=table.index)).fillna(0).gt(0).sum()
        ),
        "old_pool_exclusion_reason": "not_considered_by_fixed_pre2021_cohort; not an assessment that other identifiers were unusable",
        "diagnostic_is_not_new_strategy_eligibility": True,
        "new_dynamic_universe_built": False,
        "model_fitted": False,
        "PnL_computed": False,
        "errors": errors,
        "source_manifest_sha256": digest(daily_root / "manifest.json"),
        "cohort_manifest_sha256": digest(cohort_manifest),
        "tool_sha256": digest(Path(__file__)),
        "output_hashes": {
            name: digest(output / name) for name in ["assets.csv", "daily_diagnostic_counts.csv"]
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary), flush=True)
    if errors:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--cohort-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.daily_root, args.cohort_manifest, args.output)


if __name__ == "__main__":
    main()
