"""Dated full-catalog states and a complete source/repair ledger, with no model/PnL."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import DAY, HOUR, load_json, sha
from .data import Catalog
from .features import FEATURES, price_flow_inputs

REASONS = {
    "no_observed_activity_yet": 1,
    "no_current_positive_activity": 2,
    "invalid_daily_close": 4,
    "initial_history_warmup": 8,
    "history_reset_warmup": 16,
    "incomplete_flow_inputs": 32,
    "insufficient_funding_window": 64,
    "invalid_or_gapped_funding_window": 128,
    "stale_observable_funding": 256,
    "known_effective_order_stop": 512,
    "partial_lifecycle_day": 1024,
    "known_noncrypto_interval": 2048,
    "regular_execution_review_pending": 4096,
    "source_integrity_failure": 8192,
}


def reason_text(mask):
    return (
        "|".join(name for name, bit in REASONS.items() if int(mask) & bit)
        or "input_ready_conditional"
    )


def states_for_symbol(frame, funding):
    features = price_flow_inputs(frame, funding)
    active = frame.trade_hours.gt(0) & frame.trade_volume_sum.fillna(0).gt(0)
    ever = active.cummax()
    flags = {
        "no_observed_activity_yet": ~ever,
        "no_current_positive_activity": ~active,
        "invalid_daily_close": ~features.close_input_valid,
        "initial_history_warmup": features.initial_history_warmup,
        "history_reset_warmup": features.history_reset_warmup,
        "incomplete_flow_inputs": ~features.flow_inputs_ready,
        "insufficient_funding_window": features.funding_window_flags.map(lambda v: bool(v & 1)),
        "invalid_or_gapped_funding_window": features.funding_window_flags.map(
            lambda v: bool(v & 2)
        ),
        "stale_observable_funding": features.funding_window_flags.map(lambda v: bool(v & 4)),
        "known_effective_order_stop": frame.known_lifecycle_order_block.astype(bool),
        "partial_lifecycle_day": frame.partial_lifecycle_day.astype(bool),
        "known_noncrypto_interval": frame.known_equity_episode.astype(bool),
        "regular_execution_review_pending": frame.scoped_execution_block.astype(bool),
    }
    mask = np.zeros(len(frame), dtype=np.int64)
    for name, values in flags.items():
        mask |= values.to_numpy(dtype=np.int64) * REASONS[name]
    result = pd.DataFrame(
        {
            "instrument_id": frame.instrument_id.astype(str),
            "data_day": frame.data_day.astype(str),
            "feature_cutoff_ms": frame.reference_time_ms.astype("int64"),
            "decision_ms": frame.reference_time_ms.astype("int64") + HOUR,
            "source_episode_number": frame.episode_number.astype("int64"),
            "feature_segment_number": features.feature_segment_number.astype("int64"),
            "history_length": features.history_length.astype("int64"),
            "reason_mask": mask,
            "reason_codes": [reason_text(v) for v in mask],
            "factor_inputs_ready": active
            & features.history_length.ge(121)
            & features.flow_inputs_ready
            & features.funding_window_flags.eq(0),
            "research_candidate": mask == 0,
            "execution_ready": False,
            "lifecycle_origin_unverified": frame.lifecycle_origin_unverified.astype(bool),
            "missing_snapshot_mark": active
            & (~np.isfinite(frame.mark_close.astype(float)) | frame.mark_close.fillna(0).le(0)),
            "observed_positive_activity": active,
        }
    )
    for name in FEATURES:
        result[name] = features[name].astype(float)
    if not np.isfinite(result.loc[result.research_candidate, FEATURES].to_numpy()).all():
        raise ValueError("Nonfinite feature for provisional candidate")
    return result


def failed_states(symbol, spec):
    dates = pd.date_range(
        spec.values["source_start"],
        spec.values["source_stop"],
        inclusive="left",
        tz="UTC",
        freq="D",
    )
    size = len(dates)
    mask = REASONS["source_integrity_failure"]
    frame = pd.DataFrame(
        {
            "instrument_id": [symbol] * size,
            "data_day": dates.strftime("%Y-%m-%d"),
            "feature_cutoff_ms": dates.as_unit("ms").asi8 + DAY,
            "decision_ms": dates.as_unit("ms").asi8 + DAY + HOUR,
            "source_episode_number": np.zeros(size, dtype=np.int64),
            "feature_segment_number": np.zeros(size, dtype=np.int64),
            "history_length": np.zeros(size, dtype=np.int64),
            "reason_mask": np.full(size, mask, dtype=np.int64),
            "reason_codes": [reason_text(mask)] * size,
            "factor_inputs_ready": False,
            "research_candidate": False,
            "execution_ready": False,
            "lifecycle_origin_unverified": True,
            "missing_snapshot_mark": False,
            "observed_positive_activity": False,
        }
    )
    for name in FEATURES:
        frame[name] = np.nan
    return frame


def intervals(frame, selected=None):
    """Contiguous masks/episodes, never inferred official lifecycle boundaries."""
    changed = (
        frame.reason_mask.ne(frame.reason_mask.shift())
        | frame.source_episode_number.ne(frame.source_episode_number.shift())
        | frame.feature_segment_number.ne(frame.feature_segment_number.shift())
    )
    groups = changed.cumsum()
    rows = []
    for _, part in frame.groupby(groups, sort=False):
        if selected is not None and not selected(part):
            continue
        first, last = part.iloc[0], part.iloc[-1]
        rows.append(
            {
                "instrument_id": str(first.instrument_id),
                "source_episode_number": int(first.source_episode_number),
                "feature_segment_number": int(first.feature_segment_number),
                "from_data_day": str(first.data_day),
                "through_data_day": str(last.data_day),
                "days": len(part),
                "reason_mask": int(first.reason_mask),
                "reason_codes": str(first.reason_codes),
            }
        )
    return rows


def issue_intervals(states, source_error, policy):
    result = []
    symbol = str(states.instrument_id.iloc[0])
    flags = {
        "missing_snapshot_mark": states.missing_snapshot_mark
        & ~(states.reason_mask & REASONS["known_effective_order_stop"]).ne(0),
        "regular_execution_review": (
            states.reason_mask & REASONS["regular_execution_review_pending"]
        ).ne(0),
        "flow_input_repair": states.observed_positive_activity
        & states.history_length.ge(7)
        & (states.reason_mask & REASONS["incomplete_flow_inputs"]).ne(0),
        "funding_input_review": states.observed_positive_activity
        & states.history_length.ge(121)
        & (states.reason_mask & (64 | 128 | 256)).ne(0),
    }
    flags["invalid_active_close"] = (
        states.observed_positive_activity
        & (states.reason_mask & REASONS["invalid_daily_close"]).ne(0)
        & (
            states.reason_mask
            & (REASONS["known_effective_order_stop"] | REASONS["partial_lifecycle_day"])
        ).eq(0)
    )
    actions = {
        "invalid_active_close": "Inspect the last completed trade bar on this observed-active, nonterminal day.",
        "missing_snapshot_mark": "Check the actual required completed-hour mark; reuse verified recovery cache before any download.",
        "regular_execution_review": "Resolve the named effective execution-phase/stop policy; do not delete the whole identifier.",
        "flow_input_repair": "Inspect missing/invalid trade-hour volume inputs on these observed-active days.",
        "funding_input_review": "Inspect actual recorded funding coverage/intervals; initial funding warmup is not automatically a source defect.",
    }
    if source_error:
        return [
            {
                "instrument_id": symbol,
                "issue": "source_integrity_failure",
                "from_data_day": str(states.data_day.iloc[0]),
                "through_data_day": str(states.data_day.iloc[-1]),
                "days": len(states),
                "action": source_error,
                "policy_reasons": "",
            }
        ]
    for issue, flag in flags.items():
        groups = flag.ne(flag.shift()).cumsum()
        for _, part in states[flag].groupby(groups[flag], sort=False):
            reasons = []
            if issue == "regular_execution_review":
                a = pd.Timestamp(part.data_day.iloc[0], tz="UTC") + pd.Timedelta(days=1)
                b = pd.Timestamp(part.data_day.iloc[-1], tz="UTC") + pd.Timedelta(days=1)
                for entry in policy.get("interval_exclusions", []):
                    if (
                        entry["instrument_id"] == symbol
                        and "regular_execution" in entry["scopes"]
                        and pd.Timestamp(entry["from_utc"]) <= b
                        and pd.Timestamp(entry["to_utc"]) > a
                    ):
                        reasons.append(entry["reason"])
            result.append(
                {
                    "instrument_id": symbol,
                    "issue": issue,
                    "from_data_day": str(part.data_day.iloc[0]),
                    "through_data_day": str(part.data_day.iloc[-1]),
                    "days": len(part),
                    "action": actions[issue],
                    "policy_reasons": "|".join(sorted(set(reasons))),
                }
            )
    return result


def check_cached(folder, identity):
    meta = load_json(folder / "manifest.json")
    if meta["build_identity"] != identity:
        raise ValueError("Input identity differs from existing build")
    problems = []
    for path, digest in meta["source_bindings"].items():
        try:
            if sha(path) != digest:
                problems.append("Bound source changed: " + path)
        except OSError:
            problems.append("Bound source missing: " + path)
    for name, digest in meta["output_hashes"].items():
        try:
            if sha(folder / name) != digest:
                problems.append("Build output changed: " + name)
        except OSError:
            problems.append("Build output missing: " + name)
    if problems:
        raise ValueError(json.dumps({"cache_integrity_errors": problems}))
    return meta


def build_inputs(spec):
    import fcntl

    catalog = Catalog(spec)
    output = spec.path("output_root")
    output.mkdir(parents=True, exist_ok=True)
    code = {
        p.name: sha(p)
        for p in [
            Path(__file__),
            Path(__file__).with_name("config.py"),
            Path(__file__).with_name("data.py"),
            Path(__file__).with_name("features.py"),
        ]
    }
    from importlib.metadata import version

    identity = {
        "runtime": {name: version(name) for name in ("numpy", "pandas", "pyarrow")},
        "sources": catalog.source_identity(),
        "settings": spec.identity_values(),
        "code": code,
        "registration_sha256": sha(spec.path("registration")),
        "policy_sha256": sha(spec.path("scope_policy")),
    }
    build_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    final = output / build_id
    with (output / ".build.lock").open("a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another full-universe input build is active") from None
        if (final / "manifest.json").exists():
            meta = check_cached(final, identity)
            print(
                json.dumps({"cached": True, "success": meta["success"], "output": str(final)}),
                flush=True,
            )
            return meta, final
        if final.exists():
            raise RuntimeError("Incomplete final directory requires review; not overwriting")
        stage = output / (
            ".staging-" + build_id + "-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        )
        stage.mkdir()
        policy = load_json(spec.path("scope_policy"))
        assets = []
        all_intervals = []
        queue = []
        errors = []
        counts = []
        daily_writer = weekly_writer = None
        start = int(pd.Timestamp(spec.values["decision_start"], tz="UTC").timestamp() * 1000)
        stop = int(pd.Timestamp(spec.values["decision_stop"], tz="UTC").timestamp() * 1000)
        try:
            for number, symbol in enumerate(catalog.symbols, 1):
                error = None
                try:
                    raw = catalog.daily_frame(symbol)
                    funding = catalog.funding_frame(symbol)
                    states = states_for_symbol(raw, funding)
                except Exception as exc:
                    error = str(exc)
                    errors.append({"instrument_id": symbol, "error": error})
                    states = failed_states(symbol, spec)
                cut = pd.to_datetime(states.feature_cutoff_ms, unit="ms", utc=True)
                weekly = states[
                    (cut.dt.day_of_week == 0)
                    & states.feature_cutoff_ms.ge(start)
                    & states.feature_cutoff_ms.lt(stop)
                ].copy()
                for frame, kind in [(states, "daily"), (weekly, "weekly")]:
                    table = pa.Table.from_pandas(frame, preserve_index=False)
                    if kind == "daily":
                        if daily_writer is None:
                            daily_writer = pq.ParquetWriter(
                                stage / "daily_states.parquet", table.schema, compression="zstd"
                            )
                        daily_writer.write_table(table)
                    else:
                        if weekly_writer is None:
                            weekly_writer = pq.ParquetWriter(
                                stage / "weekly_candidates.parquet",
                                table.schema,
                                compression="zstd",
                            )
                        weekly_writer.write_table(table)
                active = states[states.observed_positive_activity]
                ready = weekly[weekly.research_candidate]
                assets.append(
                    {
                        "instrument_id": symbol,
                        "source_verified": error is None,
                        "error": error,
                        "positive_activity_days": len(active),
                        "first_observed_activity_day": active.data_day.iloc[0]
                        if len(active)
                        else None,
                        "last_observed_activity_day": active.data_day.iloc[-1]
                        if len(active)
                        else None,
                        "input_ready_days": int(states.factor_inputs_ready.sum()),
                        "candidate_decisions": len(ready),
                        "first_candidate_cutoff_ms": int(ready.feature_cutoff_ms.iloc[0])
                        if len(ready)
                        else None,
                        "max_history_length": int(states.history_length.max()),
                        "execution_ready": False,
                    }
                )
                all_intervals.extend(intervals(states))
                queue.extend(
                    issue_intervals(
                        states[
                            states.feature_cutoff_ms.ge(start) & states.feature_cutoff_ms.lt(stop)
                        ].reset_index(drop=True),
                        error,
                        policy,
                    )
                )
                counts.append(
                    weekly[
                        [
                            "feature_cutoff_ms",
                            "factor_inputs_ready",
                            "research_candidate",
                            "missing_snapshot_mark",
                        ]
                    ]
                )
                if number % 50 == 0:
                    print(
                        f"Full-catalog inputs {number}/{len(catalog.symbols)}; source_errors={len(errors)}",
                        flush=True,
                    )
            daily_writer.close()
            daily_writer = None
            weekly_writer.close()
            weekly_writer = None
            assets = pd.DataFrame(assets)
            assets.to_csv(stage / "asset_summary.csv", index=False)
            pq.write_table(
                pa.Table.from_pylist(all_intervals),
                stage / "reason_intervals.parquet",
                compression="zstd",
            )
            queue_frame = pd.DataFrame(
                queue,
                columns=[
                    "instrument_id",
                    "issue",
                    "from_data_day",
                    "through_data_day",
                    "days",
                    "action",
                    "policy_reasons",
                ],
            )
            queue_frame.to_csv(stage / "repair_queue.csv", index=False)
            count_frame = pd.concat(counts).groupby("feature_cutoff_ms").sum().astype(int)
            count_frame.to_csv(stage / "decision_counts.csv")
            daily_rows = pq.ParquetFile(stage / "daily_states.parquet").metadata.num_rows
            weekly_rows = pq.ParquetFile(stage / "weekly_candidates.parquet").metadata.num_rows
            days = len(
                pd.date_range(
                    spec.values["source_start"],
                    spec.values["source_stop"],
                    inclusive="left",
                    freq="D",
                )
            )
            if daily_rows != len(catalog.symbols) * days or weekly_rows != len(
                catalog.symbols
            ) * len(count_frame):
                raise ValueError("All-identifier daily/decision accounting mismatch")
            meta = {
                "success": not errors,
                "stage": "provisional_full_catalog_inputs",
                "build_identity": identity,
                "identifiers_expected": len(catalog.symbols),
                "identifiers_accounted": len(assets),
                "daily_rows": daily_rows,
                "weekly_rows": weekly_rows,
                "decision_dates": len(count_frame),
                "source_errors": errors,
                "identifiers_ever_provisional_candidate": int(
                    assets.candidate_decisions.gt(0).sum()
                ),
                "candidate_counts": {
                    "minimum": int(count_frame.research_candidate.min()),
                    "median": float(count_frame.research_candidate.median()),
                    "maximum": int(count_frame.research_candidate.max()),
                },
                "repair_queue_intervals": len(queue_frame),
                "repair_issue_counts": queue_frame.issue.value_counts().to_dict(),
                "execution_ready": False,
                "model_fitted": False,
                "PnL_computed": False,
                "historical_lifecycle_vintage_proven": False,
                "source_bindings": catalog.bindings,
                "output_hashes": {p.name: sha(p) for p in stage.iterdir() if p.is_file()},
            }
            (stage / "manifest.json").write_text(
                json.dumps(meta, indent=2, sort_keys=True, allow_nan=False) + "\n"
            )
            if errors:
                incomplete = output / "incomplete"
                incomplete.mkdir(exist_ok=True)
                final = incomplete / (
                    build_id + "-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
                )
            stage.rename(final)
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in meta.items()
                        if k
                        not in {
                            "source_bindings",
                            "output_hashes",
                            "build_identity",
                            "source_errors",
                        }
                    }
                    | {"source_error_count": len(errors), "output": str(final)}
                ),
                flush=True,
            )
            return meta, final
        except Exception as exc:
            (stage / "failure.json").write_text(
                json.dumps(
                    {
                        "error": str(exc),
                        "source_errors": errors,
                        "accounted_identifiers": len(assets),
                    },
                    indent=2,
                )
                + "\n"
            )
            raise
        finally:
            if daily_writer is not None:
                daily_writer.close()
            if weekly_writer is not None:
                weekly_writer.close()
