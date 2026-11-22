"""Derived scope/repair review; never changes the financial input dataset identity."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .config import load_json, sha
from .universe import REASONS


def review_inputs(dataset, root, output, prototype_manifest=None):
    dataset, root, output = Path(dataset), Path(root), Path(output)
    manifest = load_json(dataset / "manifest.json")
    for name, digest in manifest["output_hashes"].items():
        if sha(dataset / name) != digest:
            raise ValueError("Input dataset output changed: " + name)
    assets = pd.read_csv(dataset / "asset_summary.csv")
    weekly = pq.read_table(
        dataset / "weekly_candidates.parquet",
        columns=[
            "instrument_id",
            "feature_cutoff_ms",
            "reason_mask",
            "history_length",
            "observed_positive_activity",
        ],
    ).to_pandas()
    daily = pq.read_table(
        dataset / "daily_states.parquet",
        columns=["instrument_id", "data_day", "reason_mask", "observed_positive_activity"],
    ).to_pandas()
    queue = pd.read_csv(dataset / "repair_queue.csv")
    grouped = {s: g for s, g in weekly.groupby("instrument_id", sort=False)}
    for idx, asset in assets.iterrows():
        group = grouped[asset.instrument_id]
        if not asset.source_verified:
            status = "source_integrity_failure"
        elif not asset.positive_activity_days:
            status = "no_activity_in_this_release"
        elif asset.candidate_decisions > 0:
            status = "has_provisional_candidates"
        elif asset.positive_activity_days < 121:
            status = "insufficient_observed_history"
        elif asset.max_history_length < 121:
            status = "history_resets_or_close_gaps"
        elif asset.input_ready_days > 0:
            status = (
                "regular_execution_review_pending"
                if ((group.reason_mask & REASONS["regular_execution_review_pending"]) != 0).any()
                else "no_weekly_decision_after_maturity"
            )
        else:
            status = "flow_or_funding_inputs_review"
        relevant = group[group.observed_positive_activity]
        counts = {
            name: int(((relevant.reason_mask.to_numpy(dtype=np.int64) & bit) != 0).sum())
            for name, bit in REASONS.items()
        }
        assets.loc[idx, "disposition"] = status
        assets.loc[idx, "weekly_reason_counts"] = json.dumps(
            {k: v for k, v in counts.items() if v}, sort_keys=True
        )
    day_groups = {s: g for s, g in daily.groupby("instrument_id", sort=False)}
    daily_root = root / manifest["build_identity"]["settings"]["daily_root"]
    raw_cache = {}
    reviews = []

    def raw_days(symbol):
        if symbol not in raw_cache:
            path = daily_root / "daily" / (symbol + ".parquet")
            if sha(path) != manifest["source_bindings"][str(path)]:
                raise ValueError("Source daily data changed since build: " + symbol)
            raw_cache[symbol] = pq.read_table(
                path,
                columns=[
                    "data_day",
                    "trade_hours",
                    "trade_volume_sum",
                    "imbalance_inputs_valid",
                    "trade_close",
                    "episode_number",
                    "close_episode_number",
                    "known_lifecycle_order_block",
                ],
            ).to_pandas()
        return raw_cache[symbol]

    for item in queue.to_dict("records"):
        group = day_groups[item["instrument_id"]]
        subset = group[
            (group.data_day >= item["from_data_day"]) & (group.data_day <= item["through_data_day"])
        ]
        result = "needs_source_or_evidence_review"
        action = item["action"]
        affected = []
        if item["issue"] == "regular_execution_review":
            if not subset.observed_positive_activity.any():
                result = "no_observed_activity_in_interval"
                action = "No regular-entry data repair required in this inactive interval; preserve historical stop record."
            elif ((subset.reason_mask & REASONS["known_effective_order_stop"]) != 0).all():
                result = "known_effective_stop"
                action = "Preserve stop/settlement handling; do not treat regular re-entry as an unresolved data gap."
            else:
                result = "regular_mode_transition_evidence_needed"
        elif item["issue"] in {"flow_input_repair", "invalid_active_close"}:
            source = raw_days(item["instrument_id"])
            lower = (
                (pd.Timestamp(item["from_data_day"]) - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
                if item["issue"] == "flow_input_repair"
                else item["from_data_day"]
            )
            part = source[
                (source.data_day >= lower) & (source.data_day <= item["through_data_day"])
            ]
            if item["issue"] == "flow_input_repair":
                affected = part.loc[
                    part.trade_hours.lt(24) | ~part.imbalance_inputs_valid, "data_day"
                ].tolist()
                result = (
                    "inspect_exact_trade_input_days" if affected else "recheck_derived_flow_window"
                )
                first_activity = source.loc[
                    source.trade_volume_sum.fillna(0).gt(0), "data_day"
                ].min()
                if affected and all(day <= first_activity for day in affected):
                    result = "initial_listing_flow_warmup"
                    action = "Keep seven complete flow days before eligibility; do not backfill pre-listing activity."
            else:
                missing = ~np.isfinite(part.trade_close.astype(float)) | part.trade_close.fillna(
                    0
                ).le(0)
                boundary = part.episode_number.ne(part.close_episode_number)
                if (boundary & ~missing).all():
                    result = "normal_identity_boundary_reset"
                    action = "Keep history reset; no synthetic replacement close required."
                else:
                    affected = part.loc[missing, "data_day"].tolist()
                    result = "inspect_trade_close_or_episode_evidence"
        item.update(
            {
                "review_disposition": result,
                "review_action": action,
                "underlying_source_days": json.dumps(affected),
            }
        )
        reviews.append(item)
    output.mkdir(parents=True, exist_ok=True)
    assets.to_csv(output / "asset_dispositions.csv", index=False)
    review = pd.DataFrame(reviews)
    review.to_csv(output / "reviewed_queue.csv", index=False)
    counts = pd.read_csv(dataset / "decision_counts.csv")
    counts["year"] = pd.to_datetime(counts.feature_cutoff_ms, unit="ms", utc=True).dt.year
    years = counts.groupby("year").research_candidate.agg(["count", "min", "median", "max"])
    years.to_csv(output / "yearly_candidate_counts.csv")
    old = set(load_json(prototype_manifest)["symbols"]) if prototype_manifest else set()
    if old:
        comparison = weekly[["feature_cutoff_ms", "instrument_id", "reason_mask"]].copy()
        allowed = comparison.reason_mask.eq(0)
        comparison["old_cohort_candidates"] = allowed & comparison.instrument_id.isin(old)
        comparison["outside_old_cohort_candidates"] = allowed & ~comparison.instrument_id.isin(old)
        comparison.groupby("feature_cutoff_ms")[
            ["old_cohort_candidates", "outside_old_cohort_candidates"]
        ].sum().to_csv(output / "old_cohort_comparison.csv")
    ready = set(assets.loc[assets.candidate_decisions > 0, "instrument_id"])
    summary = {
        "success": manifest["success"],
        "dataset": str(dataset),
        "dataset_manifest_sha256": sha(dataset / "manifest.json"),
        "identifiers_accounted": len(assets),
        "ever_provisional_candidates": len(ready),
        "outside_old_cohort_candidates": len(ready - old) if old else None,
        "asset_disposition_counts": assets.disposition.value_counts().to_dict(),
        "reviewed_issue_counts": review.review_disposition.value_counts().to_dict()
        if len(review)
        else {},
        "candidate_counts_by_year": {
            str(int(y)): {k: int(v) if k != "median" else float(v) for k, v in row.items()}
            for y, row in years.iterrows()
        },
        "execution_ready": False,
        "model_fitted": False,
        "PnL_computed": False,
        "output_hashes": {
            p.name: sha(p) for p in output.iterdir() if p.name != "summary.json" and p.is_file()
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "output_hashes"}), flush=True)
    return summary
