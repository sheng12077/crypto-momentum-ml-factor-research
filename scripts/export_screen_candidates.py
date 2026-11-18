"""Export named screening cohorts; none is a trading-universe allowlist."""

from __future__ import annotations

import json
from pathlib import Path

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/interim/full_universe_screen_20261118"


def main():
    summary = read_json(SCREEN / "full/summary.json")
    config = read_json(SCREEN / "full/run_config.json")
    if not summary["success"] or not summary["full_scope"] or summary["errors"]:
        raise ValueError("full screening incomplete")
    if config != read_json(SCREEN / "quick/run_config.json"):
        raise ValueError("quick/full inputs differ")
    if config["inputs"]["tool_sha256"] != digest(
        (ROOT / "scripts/screen_full_universe.py").read_bytes()
    ):
        raise ValueError("screen tool changed")
    records = read_json(SCREEN / "quick/review_queue.json")
    if [r["instrument_id"] for r in records] != config["selected_symbols"]:
        raise ValueError("review population mismatch")
    cohorts = {
        k: []
        for k in (
            "active_trade",
            "three_series_active",
            "potential_Size_month_overlap",
            "possible_120_day_elapsed_span",
            "no_positive_trade_observed",
        )
    }
    hashes, rows, reports = {}, [], 0
    for record in records:
        symbol = record["instrument_id"]
        path = SCREEN / "full/checkpoints" / (symbol + ".json")
        checkpoint_hash = digest(path.read_bytes())
        if (
            read_json(SCREEN / "full/indexes" / (symbol + ".json"))["checkpoint_sha256"]
            != checkpoint_hash
        ):
            raise ValueError("checkpoint integrity failure")
        hashes[symbol] = checkpoint_hash
        result = read_json(path)
        if result["instrument_id"] != symbol or result["historical_strategy_eligible"] is not False:
            raise ValueError("invalid checkpoint identity/readiness")
        months = result["months"]
        reports += len(months)
        counts = {
            "active_trade": sum(m["positive_rows"] > 0 for m in months),
            "three_series_active": sum(m["three_series_present_with_active_trade"] for m in months),
            "potential_Size_month_overlap": sum(
                m["potential_Size_overlap_somewhere_in_month"] for m in months
            ),
            "possible_120_day_elapsed_span": sum(
                m["elapsed_120_day_history_possible_not_valid_closes"] for m in months
            ),
        }
        for key, count in counts.items():
            if count:
                cohorts[key].append(symbol)
        if counts["active_trade"] == 0:
            cohorts["no_positive_trade_observed"].append(symbol)
        rows.append({**record, "detailed_month_counts": counts})
    if reports != summary["trade_reports_verified"] or len(records) != summary["identifiers"]:
        raise ValueError("export count mismatch")
    expected = {
        "active_trade": "identifiers_with_active_trade_months",
        "three_series_active": "identifiers_with_three_series_active_months",
        "potential_Size_month_overlap": "identifiers_with_potential_Size_month_overlap",
        "possible_120_day_elapsed_span": "identifiers_with_possible_120_day_span",
    }
    if any(len(cohorts[key]) != summary[field] for key, field in expected.items()):
        raise ValueError("cohort summary mismatch")
    output = SCREEN / "exports"
    inputs = {
        "tool_sha256": digest(Path(__file__).read_bytes()),
        "full_summary_sha256": digest((SCREEN / "full/summary.json").read_bytes()),
        "quick_queue_sha256": digest((SCREEN / "quick/review_queue.json").read_bytes()),
        "checkpoint_hashes_sha256": digest(json.dumps(hashes, sort_keys=True).encode()),
    }
    with exclusive_run(output / ".export.lock"):
        bind_run(output, inputs)
        write_json(
            output / "candidate_lists.json",
            {
                "interpretation": "screening leads only; no automatic approval; cohorts are not necessarily simultaneous or the same subset",
                **cohorts,
            },
        )
        write_json(output / "review_queue.json", rows)
        result = {
            "success": True,
            "errors": [],
            "identifiers": len(rows),
            "cohort_counts": {k: len(v) for k, v in cohorts.items()},
            "Size_overlap_current_noncoin_annotations_to_review": [
                r["instrument_id"]
                for r in rows
                if r["detailed_month_counts"]["potential_Size_month_overlap"]
                and r["current_noncoin_annotation_only"]
            ],
            "Size_overlap_missing_current_metadata_retained": sum(
                bool(r["detailed_month_counts"]["potential_Size_month_overlap"])
                and r["current_metadata_missing"]
                for r in rows
            ),
            "historical_eligible_universe_ready": False,
            "OOS_performance_inspected": False,
        }
        write_json(output / "summary.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
