"""Verify a recovered Parquet's exact target partition and preserve its missing-key mask."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

from acquire_usdm_universe import digest, read_json, write_json
from reconcile_mark_gaps import HOUR, WINDOWS, milliseconds, utc


def validate(args: argparse.Namespace) -> dict:
    plan_bytes = args.plan.read_bytes()
    plan = json.loads(plan_bytes)
    manifest_path = args.version_dir / "manifest.json"
    manifest = read_json(manifest_path)
    summary = read_json(args.recovery_dir / "summary.json")
    source = args.recovery_dir / "mark_overlay.jsonl"
    parquet = args.version_dir / "mark_gap_overlay.parquet"
    if (
        digest(plan_bytes) != manifest["plan_sha256"]
        or digest(source.read_bytes()) != manifest["source_jsonl_sha256"]
    ):
        raise ValueError("overlay plan/source digest mismatch")
    if digest(parquet.read_bytes()) != manifest["parquet_sha256"] or summary["source_conflicts"]:
        raise ValueError("Parquet integrity failure or unresolved source conflict")
    if importlib.util.find_spec("pyarrow"):
        import pyarrow.parquet as pq

        rows = pq.read_table(parquet).to_pylist()
    else:
        import polars as pl

        rows = pl.read_parquet(parquet).to_dicts()
    original = {
        (r["symbol"], r["timestamp_ms"]): r
        for r in (json.loads(line) for line in source.read_text(encoding="utf-8").splitlines())
    }
    targets = {(j["symbol"], t) for j in plan["jobs"] for t in j["targets"]}
    unresolved_rows = read_json(args.recovery_dir / "unresolved.json")
    unresolved = {(r["symbol"], r["timestamp_ms"]) for r in unresolved_rows}
    observed = {(r["symbol"], r["timestamp_ms"]) for r in rows}
    if len(observed) != len(rows) or len(unresolved) != len(unresolved_rows):
        raise ValueError("duplicate recovery or missing keys")
    if observed != set(original) or observed & unresolved or observed | unresolved != targets:
        raise ValueError("recovered/missing keys do not exactly partition the frozen targets")
    if len(rows) != manifest["rows"] or len(unresolved) != manifest["unresolved_hours"]:
        raise ValueError("manifest counts differ from actual data")
    for row in rows:
        reference = original[(row["symbol"], row["timestamp_ms"])]
        if row["historical_strategy_eligible"] or row["instrument_id"] != row["symbol"]:
            raise ValueError("unexpected eligibility or instrument identity")
        if (
            milliseconds(row["timestamp"]) != row["timestamp_ms"]
            or milliseconds(row["close_timestamp"]) != row["timestamp_ms"] + HOUR - 1
        ):
            raise ValueError("Parquet timestamps differ from the exact hourly keys")
        for field in ("open", "high", "low", "close"):
            if (
                row[field + "_raw"] != reference[field]
                or row[field] != float(reference[field])
                or not math.isfinite(row[field])
            ):
                raise ValueError("Parquet price differs from verified source")
        for field in (
            "source_sha256",
            "source_url",
            "audit_after_known_lifecycle_end",
            "audit_after_last_positive_trade",
        ):
            if row[field] != reference[field]:
                raise ValueError("Parquet provenance or quality context changed")
    windows = {
        (
            milliseconds(utc(date + "T00:00:00+00:00")) - HOUR,
            milliseconds(utc(date + "T00:00:00+00:00")) + length * HOUR,
        )
        for date, length in WINDOWS
    }
    common = {
        (j["symbol"], t)
        for j in plan["jobs"]
        if (j["prior_ms"], j["next_ms"]) in windows
        for t in j["targets"]
    }
    gaps_path = args.audit_dir / "interior_gaps.json"
    if digest(gaps_path.read_bytes()) != plan["gap_file_sha256"]:
        raise ValueError("source gap audit changed")
    trade_missing = {
        (g["symbol"], t)
        for g in read_json(gaps_path)
        if g["kind"] == "trade"
        for interval in g["ranges"]
        for t in range(
            milliseconds(utc(interval["prior_observed"])) + HOUR,
            milliseconds(utc(interval["next_observed"])),
            HOUR,
        )
    }
    ranges = [
        {
            "symbol": j["symbol"],
            "month": j["month"],
            "unresolved_hours": len(set((j["symbol"], t) for t in j["targets"]) & unresolved),
            "also_missing_trade_hours": len(
                set((j["symbol"], t) for t in j["targets"]) & unresolved & trade_missing
            ),
        }
        for j in plan["jobs"]
        if any((j["symbol"], t) in unresolved for t in j["targets"])
    ]
    result = {
        "integrity_validation_passed": True,
        "recovery_complete": not unresolved,
        "verified_rows": len(rows),
        "target_hours": len(targets),
        "unresolved_hours": len(unresolved),
        "common_gap_target_hours": len(common),
        "common_gap_unresolved_hours": len(common & unresolved),
        "remaining_also_missing_trade_hours": len(unresolved & trade_missing),
        "remaining_ranges": ranges,
        "source_conflicts": 0,
        "historical_eligible_universe_ready": False,
        "export_manifest_sha256": digest(manifest_path.read_bytes()),
    }
    mask = {"validation": result, "unresolved_keys": unresolved_rows}
    destination = args.version_dir / "quality_mask.json"
    if destination.exists() and read_json(destination) != mask:
        raise ValueError("existing version quality mask differs; choose a new version")
    if not destination.exists():
        write_json(destination, mask)
    write_json(args.recovery_dir / "final_validation.json", result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "recovery-dir", "version-dir", "audit-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    validate(parser.parse_args())
