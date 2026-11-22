"""Exact required-key closure after source requests, with no readiness overstatement."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DAY, HOUR, load_json, sha
from .features import funding_windows
from .repair import baseline, write_json


def classify_required_hours(required, existing, recovered, policy_review=False):
    missing = sorted(set(required) - set(existing) - set(recovered))
    if policy_review:
        return "episode_or_policy_evidence_needed", missing
    return ("required_keys_recovered" if not missing else "required_keys_still_missing"), missing


def phase_evidence(folder, symbol):
    path = folder / "evidence" / symbol / "source.json"
    if not path.exists():
        return {"status": "phase_source_unavailable"}
    source = load_json(path)
    if sha(source["path"]) != source["sha256"]:
        raise ValueError("Phase source changed")
    article = load_json(source["path"])["data"]
    if article["code"] != source["article_code"]:
        raise ValueError("Phase article code mismatch")
    return {
        "status": "official_transition_terms_found_actual_completion_unverified",
        "title": article["title"],
        "article_code": article["code"],
        "publish_date_ms": article["publishDate"],
        "source": source,
    }


def assess_repairs(root, folder):
    root, folder = Path(root), Path(folder)
    plan, summary = load_json(folder / "plan.json"), load_json(folder / "summary.json")
    if summary["plan_sha256"] != sha(folder / "plan.json"):
        raise ValueError("Repair summary/plan mismatch")
    for name, expected in summary["output_hashes"].items():
        if sha(folder / name) != expected:
            raise ValueError("Repair output changed: " + name)
    dataset = Path(plan["dataset"])
    manifest = load_json(dataset / "manifest.json")
    if sha(dataset / "manifest.json") != plan["dataset_manifest_sha256"]:
        raise ValueError("Repair input manifest changed")
    daily_root = root / manifest["build_identity"]["settings"]["daily_root"]
    results, bases, clean, rejected = {}, {}, {}, []
    for key, job in plan["jobs"].items():
        path = folder / "jobs" / key / "result.json"
        if not path.exists():
            results[key] = {"status": "job_result_missing", "additions": []}
            continue
        if sha(path) != path.with_suffix(".sha256").read_text().strip():
            raise ValueError("Job result changed: " + key)
        result = load_json(path)
        for source in result.get("sources", []):
            if sha(source["path"]) != source["sha256"]:
                raise ValueError("Job response changed: " + key)
            if (
                "checksum_path" in source
                and sha(source["checksum_path"]) != source["checksum_sha256"]
            ):
                raise ValueError("Archive checksum changed: " + key)
        old = baseline(job)
        bases[key], results[key] = old, result
        if result["status"] != "new_observations_verified":
            continue
        for entry in result["additions"]:
            identity = (entry["kind"], entry["symbol"], entry["timestamp_ms"])
            if entry["kind"] == "funding" and len(old):
                matches = old[np.abs(old.event_timestamp_ms - entry["timestamp_ms"]) < 1000]
                if len(matches):
                    rejected.append(
                        {
                            "symbol": entry["symbol"],
                            "timestamp_ms": entry["timestamp_ms"],
                            "reason": "near_timestamp_existing_funding_event",
                        }
                    )
                    continue
            if identity in clean:
                previous = clean[identity]
                if previous.get("values", previous.get("rate")) != entry.get(
                    "values", entry.get("rate")
                ):
                    raise ValueError("Conflicting recovered observations: " + str(identity))
            else:
                clean[identity] = entry
    grouped, raw_daily = {}, {}
    for entry in clean.values():
        grouped.setdefault((entry["kind"], entry["symbol"]), []).append(entry)

    def source_days(symbol):
        if symbol not in raw_daily:
            path = daily_root / "daily" / (symbol + ".parquet")
            if sha(path) != manifest["source_bindings"][str(path)]:
                raise ValueError("Daily source changed: " + symbol)
            raw_daily[symbol] = pd.read_parquet(
                path,
                columns=[
                    "data_day",
                    "partial_lifecycle_day",
                    "episode_number",
                    "close_episode_number",
                ],
            )
        return raw_daily[symbol]

    cases, missing_keys, phases = [], [], {}
    for original in plan["cases"]:
        case = dict(original)
        symbol, issue = case["instrument_id"], case["issue"]
        jobs = case["job_ids"]
        if not jobs:
            if case["initial_disposition"] in {
                "initial_listing_flow_warmup",
                "known_effective_stop",
            }:
                state = case["initial_disposition"]
            elif issue == "regular_execution_review":
                phases[symbol] = phase_evidence(folder, symbol)
                state = phases[symbol]["status"]
            else:
                state = case["initial_disposition"]
            missing = []
        elif any(
            results[key]["status"] in {"source_conflict", "integrity_failure", "job_result_missing"}
            for key in jobs
        ):
            state, missing = "blocked_source_conflict_or_integrity", []
        elif any(results[key]["status"] == "unresolved_source_request" for key in jobs):
            state, missing = "unresolved_source_request", []
        elif issue == "funding_input_review":
            frames = [bases[key] for key in jobs if len(bases[key])]
            old = (
                pd.concat(frames, ignore_index=True)
                .drop_duplicates("event_timestamp_ms")
                .sort_values("event_timestamp_ms")
                if frames
                else pd.DataFrame(
                    columns=["event_timestamp_ms", "funding_rate", "funding_interval_hours"]
                )
            )
            entries = [
                entry
                for entry in grouped.get(("funding", symbol), [])
                if any(
                    plan["jobs"][key]["start_ms"]
                    <= entry["timestamp_ms"]
                    < plan["jobs"][key]["stop_ms"]
                    for key in jobs
                )
            ]
            safe = [entry for entry in entries if entry["funding_interval_hours"] is not None]
            if safe:
                added = pd.DataFrame(
                    {
                        "event_timestamp_ms": [entry["timestamp_ms"] for entry in safe],
                        "funding_rate": [entry["rate"] for entry in safe],
                        "funding_interval_hours": [
                            entry["funding_interval_hours"] for entry in safe
                        ],
                    }
                )
                old = (
                    pd.concat([old, added], ignore_index=True)
                    .drop_duplicates("event_timestamp_ms")
                    .sort_values("event_timestamp_ms")
                )
            dates = pd.date_range(case["from_data_day"], case["through_data_day"], tz="UTC")
            cutoffs = dates.as_unit("ms").asi8 + DAY
            _, flags = funding_windows(old, cutoffs)
            case["funding_cutoffs_insufficient_duration"] = int(((flags & 1) != 0).sum())
            case["funding_cutoffs_gap_or_invalid"] = int(((flags & 2) != 0).sum())
            case["funding_cutoffs_stale"] = int(((flags & 4) != 0).sum())
            missing = [int(t) for t, flag in zip(cutoffs, flags, strict=True) if flag]
            state = (
                "funding_windows_recovered"
                if not missing
                else "retrieved_rates_interval_metadata_unverified"
                if len(safe) < len(entries)
                else "funding_windows_still_incomplete_after_official_check"
            )
            case["new_rates_without_verified_interval"] = len(entries) - len(safe)
            if missing and not ((flags & 6) != 0).any() and len(safe) == len(entries):
                state = "reported_duration_only_rule_review"
        else:
            kind = "mark" if issue == "missing_snapshot_mark" else "trade"
            source = source_days(symbol)
            days = (
                json.loads(case["underlying_source_days"])
                if issue == "flow_input_repair"
                else pd.date_range(case["from_data_day"], case["through_data_day"])
                .strftime("%Y-%m-%d")
                .tolist()
            )
            affected = source[source.data_day.isin(days)]
            policy_review = bool(
                affected.partial_lifecycle_day.any()
                or affected.episode_number.ne(affected.close_episode_number).any()
            )
            required = []
            for day in days:
                start = int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)
                required.extend(
                    range(start, start + DAY, HOUR)
                    if issue == "flow_input_repair"
                    else [start + 23 * HOUR]
                )
            existing = set()
            for key in jobs:
                old = bases[key]
                if len(old):
                    valid = np.isfinite(old.close.astype(float)) & old.close.gt(0)
                    if issue == "flow_input_repair":
                        valid &= (
                            np.isfinite(old.quote_volume.astype(float))
                            & old.quote_volume.ge(0)
                            & old.taker_buy_quote_volume.ge(0)
                            & old.taker_buy_quote_volume.le(old.quote_volume + 1e-8)
                        )
                    existing.update(int(t) for t in old.loc[valid, "bar_open_ms"])
            recovered = {entry["timestamp_ms"] for entry in grouped.get((kind, symbol), [])}
            state, missing = classify_required_hours(required, existing, recovered, policy_review)
            if (
                issue == "flow_input_repair"
                and len(affected) == len(days)
                and affected.partial_lifecycle_day.all()
            ):
                state = "known_partial_event_day_flow_warmup"
                case["expected_nonfull_event_day_hours"] = len(missing)
                missing = []
        case["verified_disposition"] = state
        case["unresolved_required_keys"] = len(missing)
        case["job_ids"] = json.dumps(jobs)
        cases.append(case)
        missing_keys.extend(
            {
                "case_id": case["case_id"],
                "instrument_id": symbol,
                "issue": issue,
                "timestamp_ms": t,
                "meaning": "feature_cutoff_with_incomplete_funding"
                if issue == "funding_input_review"
                else "required_hour_open",
            }
            for t in missing
        )
    pd.DataFrame(cases).to_csv(folder / "verified_case_dispositions.csv", index=False)
    pd.DataFrame(
        missing_keys, columns=["case_id", "instrument_id", "issue", "timestamp_ms", "meaning"]
    ).to_csv(folder / "remaining_required_keys.csv", index=False)
    with (folder / "deduplicated_observations.jsonl").open("w") as stream:
        for identity in sorted(clean):
            stream.write(json.dumps(clean[identity], sort_keys=True, allow_nan=False) + "\n")
    write_json(folder / "phase_evidence.json", phases)
    output = {
        "all_cases_accounted": len(cases) == len(plan["cases"]),
        "cases": len(cases),
        "verified_disposition_counts": pd.Series([case["verified_disposition"] for case in cases])
        .value_counts()
        .to_dict(),
        "unique_new_rows_by_kind": pd.Series([identity[0] for identity in clean])
        .value_counts()
        .to_dict(),
        "rejected_aliases": len(rejected),
        "remaining_required_key_rows": len(missing_keys),
        "execution_ready": False,
        "canonical_data_modified": False,
        "PnL_computed": False,
        "source_repair_summary_sha256": sha(folder / "summary.json"),
        "assessment_code_sha256": sha(Path(__file__)),
        "output_hashes": {
            name: sha(folder / name)
            for name in [
                "verified_case_dispositions.csv",
                "remaining_required_keys.csv",
                "deduplicated_observations.jsonl",
                "phase_evidence.json",
            ]
        },
    }
    write_json(folder / "assessment.json", output)
    print(json.dumps(output), flush=True)
    return output
