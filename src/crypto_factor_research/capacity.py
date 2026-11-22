"""Dated entry-capacity diagnostics; future holding risks are never entry filters."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DAY, HOUR, load_json, sha
from .repair import baseline, write_json


def dated_candidates(weekly, metadata):
    frame = weekly.copy()
    types = frame.instrument_id.map({s: v.get("underlyingType") for s, v in metadata.items()})
    onboard = frame.instrument_id.map({s: v.get("onboardDate") for s, v in metadata.items()})
    started = onboard.notna() & frame.feature_cutoff_ms.ge(onboard)
    out = started & ~types.isin(["COIN", "PREMARKET"])
    pending = started & types.eq("PREMARKET")
    frame["snapshot_underlying_type"] = types.fillna("NOT_IN_CURRENT_RESPONSE")
    frame["dated_out_of_single_crypto_scope"] = out
    frame["dated_current_premarket_pending"] = pending
    frame["dated_current_coin_support"] = started & types.eq("COIN")
    frame["historical_class_unresolved"] = ~(out | pending | frame.dated_current_coin_support)
    frame["provisional_entry_candidate"] = frame.research_candidate & ~out & ~pending
    frame["current_coin_supported_candidate"] = (
        frame.provisional_entry_candidate & frame.dated_current_coin_support
    )
    frame["execution_ready"] = False
    return frame


def nominal_breaks(symbol, old, observed_additions):
    """Same-interval missing slots only; no assertion that a payment was charged."""
    if old.empty:
        return []
    old = old.sort_values("event_timestamp_ms").drop_duplicates("event_timestamp_ms")
    known = np.array(sorted(int(x["timestamp_ms"]) for x in observed_additions), dtype=np.int64)
    rows = old.to_dict("records")
    result = []
    for a, b in zip(rows, rows[1:], strict=False):
        interval = float(a["funding_interval_hours"])
        other = float(b["funding_interval_hours"])
        if not math.isfinite(interval) or interval <= 0 or interval != other:
            continue
        before, after = int(a["event_timestamp_ms"]), int(b["event_timestamp_ms"])
        step = int(interval * HOUR)
        difference = after - before
        if difference <= step + 1000:
            continue
        periods = round(difference / step)
        if periods < 2 or abs(difference - periods * step) > 1000:
            continue
        if periods > 24 * 366:
            raise ValueError("Unexpected unbounded funding observation break")
        anchor = round(before / HOUR) * HOUR
        if abs(before - anchor) > 1000:
            anchor = before
        for k in range(1, periods):
            t = anchor + k * step
            left = np.searchsorted(known, t - 1000)
            right = np.searchsorted(known, t + 1000, side="right")
            if right > left:
                continue
            result.append(
                {
                    "instrument_id": symbol,
                    "nominal_event_ms": t,
                    "previous_record_ms": before,
                    "next_record_ms": after,
                    "recorded_interval_hours": interval,
                    "meaning": "absent_observation_not_proven_payment",
                }
            )
    return result


def breaks_in_job(job, old, observed_additions):
    """Do not bridge two separately requested source windows across uninspected months."""
    if old.empty:
        return []
    valid = old.funding_interval_hours[
        np.isfinite(old.funding_interval_hours) & old.funding_interval_hours.gt(0)
    ]
    margin = int(valid.max() * HOUR + 1000) if len(valid) else HOUR
    near = old[
        old.event_timestamp_ms.ge(job["start_ms"] - margin)
        & old.event_timestamp_ms.le(job["stop_ms"] + margin)
    ]
    return [
        row
        for row in nominal_breaks(job["symbol"], near, observed_additions)
        if job["start_ms"] <= row["nominal_event_ms"] < job["stop_ms"]
    ]


def holding_audit(frame, breaks, horizons=(7, 14, 28)):
    result = frame.copy()
    for days in horizons:
        result[f"known_funding_breaks_next_{days}d"] = 0
    mapping = (
        {s: np.sort(g.nominal_event_ms.unique()) for s, g in breaks.groupby("instrument_id")}
        if len(breaks)
        else {}
    )
    for symbol, group in result.groupby("instrument_id", sort=False):
        stamps = mapping.get(symbol, np.array([], dtype=np.int64))
        t = group.decision_ms.to_numpy(dtype=np.int64)
        left = np.searchsorted(stamps, t, side="right")
        for days in horizons:
            right = np.searchsorted(stamps, t + days * DAY, side="right")
            result.loc[group.index, f"known_funding_breaks_next_{days}d"] = right - left
    return result


def below_periods(counts, column, threshold):
    flag = counts[column].lt(threshold)
    groups = flag.ne(flag.shift()).cumsum()
    return [
        {
            "pool": column,
            "threshold": threshold,
            "first_cutoff_ms": int(g.feature_cutoff_ms.iloc[0]),
            "last_cutoff_ms": int(g.feature_cutoff_ms.iloc[-1]),
            "weekly_decisions": len(g),
            "minimum": int(g[column].min()),
        }
        for _, g in counts[flag].groupby(groups[flag], sort=False)
    ]


def verify_outputs(folder, meta):
    for name, expected in meta["output_hashes"].items():
        if sha(folder / name) != expected:
            raise ValueError("Bound output changed: " + str(folder / name))


def capacity_audit(root, repair_dir):
    root, repair_dir = Path(root), Path(repair_dir)
    plan = load_json(repair_dir / "plan.json")
    assessment = load_json(repair_dir / "assessment.json")
    verify_outputs(repair_dir, assessment)
    repair_summary = load_json(repair_dir / "summary.json")
    if (
        sha(repair_dir / "summary.json") != assessment["source_repair_summary_sha256"]
        or sha(repair_dir / "plan.json") != repair_summary["plan_sha256"]
    ):
        raise ValueError("Repair plan/assessment chain changed")
    dataset = Path(plan["dataset"])
    manifest = load_json(dataset / "manifest.json")
    if sha(dataset / "manifest.json") != plan["dataset_manifest_sha256"]:
        raise ValueError("Dataset manifest changed")
    verify_outputs(dataset, manifest)
    source = load_json(repair_dir / "evidence/exchange_info/source.json")
    if sha(source["path"]) != source["sha256"]:
        raise ValueError("Product metadata changed")
    identity = {
        "dataset_manifest_sha256": sha(dataset / "manifest.json"),
        "repair_assessment_sha256": sha(repair_dir / "assessment.json"),
        "metadata_source_sha256": source["sha256"],
        "registration_sha256": sha(root / "experiments/019_dynamic_universe_capacity.md"),
        "code_sha256": sha(Path(__file__)),
        "repair_reader_sha256": sha(Path(__file__).with_name("repair.py")),
        "config_reader_sha256": sha(Path(__file__).with_name("config.py")),
        "runtime": {"numpy": np.__version__, "pandas": pd.__version__},
        "holding_horizons_days": [7, 14, 28],
        "liquidity_filter_applied": False,
        "repair_overlay_integrated": False,
    }
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    parent = root / "reports/tables/dynamic_universe_capacity"
    output = parent / run_id
    if (output / "summary.json").exists():
        cached = load_json(output / "summary.json")
        if cached["identity"] != identity:
            raise ValueError("Diagnostic identity mismatch")
        verify_outputs(output, cached)
        for path, expected in cached["source_bindings"].items():
            if sha(path) != expected:
                raise ValueError("Cached audit source changed: " + path)
        print(json.dumps({"cached": True, "output": str(output)}), flush=True)
        return cached
    parent.mkdir(parents=True, exist_ok=True)
    stage = parent / (".staging-" + run_id)
    stage.mkdir()
    weekly = pd.read_parquet(dataset / "weekly_candidates.parquet")
    if (
        len(weekly) != manifest["weekly_rows"]
        or weekly.instrument_id.nunique() != manifest["identifiers_accounted"]
    ):
        raise ValueError("Full-identifier weekly accounting mismatch")
    metadata = {x["symbol"]: x for x in load_json(source["path"])["symbols"]}
    panel = dated_candidates(weekly, metadata)
    added = [
        json.loads(line)
        for line in (repair_dir / "deduplicated_observations.jsonl").read_text().splitlines()
        if line
    ]
    additions = {}
    for row in added:
        if row["kind"] == "funding":
            additions.setdefault(row["symbol"], []).append(row)
    slots, source_bindings = [], {}
    for key, job in plan["jobs"].items():
        if job["kind"] != "funding":
            continue
        result_path = repair_dir / "jobs" / key / "result.json"
        if sha(result_path) != result_path.with_suffix(".sha256").read_text().strip():
            raise ValueError("Funding verification checkpoint changed")
        result = load_json(result_path)
        for record in result.get("sources", []):
            if sha(record["path"]) != record["sha256"]:
                raise ValueError("Official funding response changed")
            source_bindings[record["path"]] = record["sha256"]
        old = baseline(job)
        source_bindings.update(job["baselines"])
        slots.extend(breaks_in_job(job, old, additions.get(job["symbol"], [])))
    breaks = pd.DataFrame(
        slots,
        columns=[
            "instrument_id",
            "nominal_event_ms",
            "previous_record_ms",
            "next_record_ms",
            "recorded_interval_hours",
            "meaning",
        ],
    ).drop_duplicates(["instrument_id", "nominal_event_ms"])
    panel = holding_audit(panel, breaks)
    pd.testing.assert_series_equal(
        panel.provisional_entry_candidate,
        dated_candidates(weekly, metadata).provisional_entry_candidate,
    )
    recovered_marks = {(x["symbol"], x["timestamp_ms"]) for x in added if x["kind"] == "mark"}
    panel["prior_daily_close_mark_still_missing"] = panel.missing_snapshot_mark & pd.Series(
        [
            (s, int(t) - HOUR) not in recovered_marks
            for s, t in zip(panel.instrument_id, panel.feature_cutoff_ms, strict=True)
        ],
        index=panel.index,
    )
    panel.to_parquet(stage / "dated_candidates.parquet", index=False)
    breaks.to_csv(stage / "known_funding_observation_breaks.csv", index=False)
    contributions = pd.DataFrame(
        {
            "feature_cutoff_ms": panel.feature_cutoff_ms,
            "original_provisional": panel.research_candidate.astype(int),
            "dated_crypto_provisional": panel.provisional_entry_candidate.astype(int),
            "current_coin_supported": panel.current_coin_supported_candidate.astype(int),
            "candidate_class_unresolved": (
                panel.provisional_entry_candidate & panel.historical_class_unresolved
            ).astype(int),
            "candidate_prior_daily_mark_missing": (
                panel.provisional_entry_candidate & panel.prior_daily_close_mark_still_missing
            ).astype(int),
        }
    )
    for days in [7, 14, 28]:
        contributions[f"candidate_known_gap_next_{days}d"] = (
            panel.provisional_entry_candidate & panel[f"known_funding_breaks_next_{days}d"].gt(0)
        ).astype(int)
    counts = contributions.groupby("feature_cutoff_ms", as_index=False).sum()
    counts["year"] = pd.to_datetime(counts.feature_cutoff_ms, unit="ms", utc=True).dt.year
    counts.to_csv(stage / "weekly_counts.csv", index=False)
    year_rows = []
    for year, g in counts.groupby("year"):
        for pool in ["dated_crypto_provisional", "current_coin_supported"]:
            values = g[pool]
            year_rows.append(
                {
                    "year": int(year),
                    "pool": pool,
                    "weeks": len(g),
                    "minimum": int(values.min()),
                    "median": float(values.median()),
                    "maximum": int(values.max()),
                    "fraction_at_least_100": float(values.ge(100).mean()),
                    "fraction_at_least_200": float(values.ge(200).mean()),
                }
            )
    pd.DataFrame(year_rows).to_csv(stage / "yearly_capacity.csv", index=False)
    periods = [
        p
        for pool in ["dated_crypto_provisional", "current_coin_supported"]
        for threshold in [100, 200]
        for p in below_periods(counts, pool, threshold)
    ]
    pd.DataFrame(periods).to_csv(stage / "below_threshold_periods.csv", index=False)
    assets = panel.groupby("instrument_id").agg(
        original_candidate_weeks=("research_candidate", "sum"),
        dated_crypto_candidate_weeks=("provisional_entry_candidate", "sum"),
        coin_supported_weeks=("current_coin_supported_candidate", "sum"),
        unresolved_class_weeks=("historical_class_unresolved", "sum"),
    )
    assets.to_csv(stage / "asset_dispositions.csv")
    count_cols = ["dated_crypto_provisional", "current_coin_supported"]
    meta = {
        "identity": identity,
        "identifiers_accounted": len(assets),
        "weekly_rows": len(panel),
        "weekly_decisions": len(counts),
        "ever_dated_provisional_identifiers": int(assets.dated_crypto_candidate_weeks.gt(0).sum()),
        "yearly_capacity": year_rows,
        "minimum_since_2022": {
            c: int(counts.loc[counts.year.ge(2022), c].min()) for c in count_cols
        },
        "fraction_at_least_100_since_2022": {
            c: float(counts.loc[counts.year.ge(2022), c].ge(100).mean()) for c in count_cols
        },
        "known_funding_observation_breaks": len(breaks),
        "candidate_dates_with_known_future_14d_break": int(
            counts.candidate_known_gap_next_14d.gt(0).sum()
        ),
        "maximum_candidate_count_with_future_14d_break": int(
            counts.candidate_known_gap_next_14d.max()
        ),
        "holding_audit_coverage": "known same-frequency breaks in bounded checked source evidence only;not complete funding-cost certification",
        "snapshot_scope_is_retrospective_assumption": True,
        "future_risk_used_as_entry_filter": False,
        "repair_overlay_integrated": False,
        "liquidity_or_capacity_qualified": False,
        "execution_ready": False,
        "PnL_computed": False,
        "source_bindings": source_bindings,
        "output_hashes": {f.name: sha(f) for f in stage.iterdir() if f.is_file()},
    }
    write_json(stage / "summary.json", meta)
    stage.rename(output)
    print(
        json.dumps(
            {
                k: v
                for k, v in meta.items()
                if k not in {"source_bindings", "output_hashes", "identity"}
            }
            | {"output": str(output)}
        ),
        flush=True,
    )
    return meta
