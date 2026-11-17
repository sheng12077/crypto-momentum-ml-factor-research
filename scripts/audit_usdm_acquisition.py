"""Read-only source integrity, gap geometry and lifecycle-review audit."""

from __future__ import annotations

import argparse
import calendar
import json
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

from acquire_usdm_universe import (
    bind_run,
    cancellable_pool,
    digest,
    exclusive_run,
    read_json,
    validate_file_record,
    verify_payload,
    write_json,
)


def as_time(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def gap_geometry(quality: dict, month: str) -> dict:
    expected = calendar.monthrange(*map(int, month.split("-")))[1] * 24
    if quality["row_count"] == 0:
        return {
            "expected": expected,
            "boundary_missing": expected,
            "interior_missing": 0,
            "classification": "empty",
        }
    first, last = as_time(quality["first_time"]), as_time(quality["last_time"])
    if first.strftime("%Y-%m") != month or last.strftime("%Y-%m") != month:
        raise ValueError("reported time bounds outside source month")
    span = (last - first).total_seconds() / 3600 + 1
    if span != int(span) or span < quality["row_count"] or span > expected:
        raise ValueError("inconsistent hourly row geometry")
    interior, boundary = int(span) - quality["row_count"], expected - int(span)
    if quality["missing_hourly_rows"] != interior + boundary:
        raise ValueError("reported missing-hour count disagrees with geometry")
    return {
        "expected": expected,
        "boundary_missing": boundary,
        "interior_missing": interior,
        "classification": "interior_gap"
        if interior
        else "boundary_only"
        if boundary
        else "complete",
    }


def read_gap_ranges(path: Path, expected_rows: int) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].file_size > 10 * 1024 * 1024:
            raise ValueError("unexpected ZIP members or decompressed size")
        raw = archive.read(members[0]).decode("utf-8-sig")
    timestamps = []
    for line in raw.splitlines():
        value = line.split(",", 1)[0]
        if value == "open_time":
            continue
        stamp = int(value)
        timestamps.append(datetime.fromtimestamp(stamp / (10**6 if stamp >= 10**14 else 1000), UTC))
    if len(timestamps) != expected_rows or timestamps != sorted(set(timestamps)):
        raise ValueError("raw timestamps disagree with report, duplicate, or unordered")
    ranges = []
    for first, last in pairwise(timestamps):
        hours = (last - first).total_seconds() / 3600
        if hours != int(hours) or hours < 1:
            raise ValueError("off-grid timestamps")
        if hours > 1:
            ranges.append(
                {
                    "prior_observed": first.isoformat(),
                    "next_observed": last.isoformat(),
                    "missing_hours": int(hours) - 1,
                }
            )
    return ranges


def verify_report(report_path: Path, plan_row: dict, data_root: Path) -> dict:
    report = read_json(report_path)
    for field in ("key", "symbol", "kind", "month"):
        if report[field] != plan_row[field]:
            raise ValueError(f"report/plan mismatch: {field}")
    filename = validate_file_record(plan_row)
    raw_path = Path(report["path"]).resolve()
    if not raw_path.is_relative_to((data_root / "raw").resolve()):
        raise ValueError("raw path escapes shared raw data root")
    body = raw_path.read_bytes()
    checksum = raw_path.with_name(filename + ".CHECKSUM").read_bytes()
    sha = verify_payload(body, checksum, filename, plan_row["size"])
    metadata = read_json(raw_path.with_name(filename + ".metadata.json"))
    url = "https://data.binance.vision/" + urllib.parse.quote(report["key"], safe="/")
    if report["sha256"] != sha or report["bytes"] != len(body) or report["source_url"] != url:
        raise ValueError("report hash/size/source mismatch")
    if metadata["sha256"] != sha or metadata["byte_size"] != len(body):
        raise ValueError("raw provenance hash/size mismatch")
    if metadata.get("archive_url", metadata.get("source_url")) != url:
        raise ValueError("raw provenance URL mismatch")
    if metadata.get("retrieved_at") != report["retrieved_at"]:
        raise ValueError("raw provenance acquisition time mismatch")
    geometry, gaps = None, []
    if report["kind"] != "funding":
        geometry = gap_geometry(report["quality"], report["month"])
        if geometry["interior_missing"]:
            gaps = read_gap_ranges(raw_path, report["quality"]["row_count"])
            if sum(g["missing_hours"] for g in gaps) != geometry["interior_missing"]:
                raise ValueError("raw gap count disagrees with report geometry")
    return {**report, "geometry": geometry, "interior_gap_ranges": gaps}


def aggregate_symbol(identity: dict, reports: list[dict]) -> dict:
    trade = sorted((r for r in reports if r["kind"] == "trade"), key=lambda r: r["month"])
    mark = [r for r in reports if r["kind"] == "mark"]
    funding = [r for r in reports if r["kind"] == "funding"]
    first_positive = min(
        (
            r["quality"]["first_positive_volume_time"]
            for r in trade
            if r["quality"]["first_positive_volume_time"]
        ),
        default=None,
    )
    last_positive = max(
        (
            r["quality"]["last_positive_volume_time"]
            for r in trade
            if r["quality"]["last_positive_volume_time"]
        ),
        default=None,
    )
    artifact_months = [
        r["month"] for r in trade if r["quality"]["zero_volume_constant_trade_artifact"]
    ]
    geometry = Counter(r["geometry"]["classification"] for r in reports if r["geometry"])
    interior_hours = sum(r["geometry"]["interior_missing"] for r in reports if r["geometry"])
    funding_later = [
        r
        for r in funding
        if last_positive and as_time(r["quality"]["first_time"]) > as_time(last_positive)
    ]
    observed_end = max((r["quality"]["last_time"] for r in trade), default=None)
    flags = []
    if identity["current_noncoin_annotation"]:
        flags.append("current_noncoin_annotation_not_crypto_eligibility")
    if identity["current_product_metadata"] is None:
        flags.append("identity_missing_from_current_snapshot")
    if artifact_months:
        flags.append("constant_zero_volume_trade_files")
    if interior_hours:
        flags.append("interior_price_or_mark_gaps")
    if funding_later:
        flags.append("funding_files_start_after_last_positive_trade_observation")
    if not first_positive:
        flags.append("no_positive_volume_trade_observed_in_window")
    event_checks = []
    for event in identity.get("lifecycle_events", []):
        effective = as_time(event["effective_at"])
        event_checks.append(
            {
                "event": event,
                "last_positive_trade_bar_start": last_positive,
                "positive_bar_start_at_or_after_event": bool(
                    last_positive and as_time(last_positive) >= effective
                ),
            }
        )
    return {
        "symbol": identity["instrument_id"],
        "file_count": len(reports),
        "current_metadata": identity["current_product_metadata"],
        "first_positive_trade_bar": first_positive,
        "last_positive_trade_bar": last_positive,
        "last_trade_archive_row": observed_end,
        "trade_files": len(trade),
        "mark_files": len(mark),
        "funding_files": len(funding),
        "constant_zero_volume_trade_months": artifact_months,
        "gap_file_counts": dict(geometry),
        "interior_missing_hours_trade_and_mark": interior_hours,
        "funding_files_starting_after_last_positive_trade": len(funding_later),
        "funding_rows_in_those_files": sum(r["quality"]["row_count"] for r in funding_later),
        "review_flags": flags,
        "lifecycle_event_checks": event_checks,
        "activity_bounds_are_ex_post_not_causal_eligibility": True,
        "historical_strategy_eligible": False,
    }


def write_review_rollup(audit_dir: Path, census_dir: Path, download_dir: Path) -> dict:
    """Summarize already audited reports; never reinterprets them as eligibility."""
    summary = read_json(audit_dir / "summary.json")
    if not summary["success"]:
        raise ValueError("requires a successful source-integrity audit")
    symbols = read_json(audit_dir / "symbol_quality.json")
    gaps = read_json(audit_dir / "interior_gaps.json")
    coverage = read_json(census_dir / "coverage.json")
    classes = defaultdict(Counter)
    for symbol in symbols:
        metadata = symbol["current_metadata"]
        label = (
            "unknown"
            if metadata is None
            else "current_COIN"
            if metadata.get("underlyingType") == "COIN"
            else "current_nonCOIN"
        )
        classes[label]["symbols"] += 1
        classes[label]["constant_trade_symbols"] += bool(
            symbol["constant_zero_volume_trade_months"]
        )
        classes[label]["interior_gap_symbols"] += bool(
            symbol["interior_missing_hours_trade_and_mark"]
        )
        classes[label]["funding_after_activity_symbols"] += bool(
            symbol["funding_files_starting_after_last_positive_trade"]
        )
    signatures = defaultdict(set)
    for file in gaps:
        for gap in file["ranges"]:
            signatures[
                (file["kind"], gap["prior_observed"], gap["next_observed"], gap["missing_hours"])
            ].add(file["symbol"])
    common = [
        {
            "kind": key[0],
            "prior_observed": key[1],
            "next_observed": key[2],
            "missing_hours_each": key[3],
            "symbol_count": len(value),
            "symbols": sorted(value),
        }
        for key, value in signatures.items()
    ]
    common.sort(key=lambda row: (-row["symbol_count"], row["prior_observed"]))
    month_gaps = {}
    for kind in ("trade", "mark", "funding"):
        affected = [
            {
                "symbol": row["instrument_id"],
                "months": row["series"][kind].get("missing_interior_months", []),
            }
            for row in coverage
            if row["series"][kind].get("missing_interior_months")
        ]
        month_gaps[kind] = {
            "affected_symbols": len(affected),
            "missing_months": sum(len(row["months"]) for row in affected),
            "details": affected,
        }
    bounds = defaultdict(lambda: defaultdict(dict))
    count = 0
    for path in (download_dir / "files").glob("*.json"):
        row = read_json(path)
        target = bounds[row["symbol"]][row["kind"]]
        for field, choose in (("first_time", min), ("last_time", max)):
            value = row["quality"][field]
            if value:
                target[field] = choose(target.get(field, value), value)
        count += 1
    if count != summary["verified_raw_files"]:
        raise ValueError("report corpus changed after source audit")
    result = {
        "source_audit_summary_sha256": digest((audit_dir / "summary.json").read_bytes()),
        "current_classification_diagnostics": {k: dict(v) for k, v in classes.items()},
        "whole_month_interior_gaps": month_gaps,
        "common_gap_patterns": common,
        "trade_gap_files": [row for row in gaps if row["kind"] == "trade"],
        "causal_eligibility": False,
    }
    write_json(audit_dir / "review_rollup.json", result)
    write_json(audit_dir / "series_observed_bounds.json", bounds)
    return result


def run(args: argparse.Namespace) -> bool:
    plan_bytes = (args.census_dir / "download_plan.json").read_bytes()
    plan = json.loads(plan_bytes)
    download_summary = read_json(args.download_dir / "summary.json")
    bind_run(
        args.output_dir,
        {
            "operation": "post_acquisition_audit",
            "schema": 1,
            "plan_sha256": digest(plan_bytes),
            "download_summary_sha256": digest((args.download_dir / "summary.json").read_bytes()),
        },
    )
    files = {row["key"]: row for row in plan["files"]}
    if len(files) != len(plan["files"]) or not download_summary["success"]:
        raise ValueError("duplicate plan keys or incomplete acquisition")
    report_paths = list((args.download_dir / "files").glob("*.json"))
    expected_names = {digest(key.encode()) + ".json" for key in files}
    observed_names = {p.name for p in report_paths}
    reconciliation = {
        "expected_files": len(files),
        "observed_reports": len(report_paths),
        "missing_reports": sorted(expected_names - observed_names),
        "unplanned_reports": sorted(observed_names - expected_names),
        "summary_count_matches_plan": download_summary["verified_files"] == len(files),
        "summary_bytes_match_plan": download_summary["verified_bytes"]
        == sum(r["size"] for r in files.values()),
    }
    reconciled = not reconciliation["missing_reports"] and not reconciliation["unplanned_reports"]
    reconciled = (
        reconciled
        and reconciliation["summary_count_matches_plan"]
        and reconciliation["summary_bytes_match_plan"]
    )
    verified, errors = [], []
    with cancellable_pool(args.workers) as pool:
        pending = {
            pool.submit(
                verify_report,
                args.download_dir / "files" / (digest(key.encode()) + ".json"),
                row,
                args.data_root,
            ): key
            for key, row in files.items()
        }
        from concurrent.futures import as_completed

        for index, future in enumerate(as_completed(pending), 1):
            try:
                verified.append(future.result())
            except Exception as exc:
                errors.append({"key": pending[future], "error": str(exc)})
            if index % 10000 == 0 or index == len(files):
                print(f"source audit {index}/{len(files)}; errors={len(errors)}", flush=True)
    by_symbol = defaultdict(list)
    for report in verified:
        by_symbol[report["symbol"]].append(report)
    identities = read_json(args.census_dir / "identity_ledger.json")
    symbols = [
        aggregate_symbol(identity, by_symbol[identity["instrument_id"]]) for identity in identities
    ]
    geometry = Counter(r["geometry"]["classification"] for r in verified if r["geometry"])
    by_kind = {}
    for kind in ("trade", "mark", "funding"):
        group = [r for r in verified if r["kind"] == kind]
        by_kind[kind] = {
            "files": len(group),
            "rows": sum(r["quality"]["row_count"] for r in group),
            "boundary_only_files": sum(
                r["geometry"] is not None and r["geometry"]["classification"] == "boundary_only"
                for r in group
            ),
            "interior_gap_files": sum(
                r["geometry"] is not None and r["geometry"]["classification"] == "interior_gap"
                for r in group
            ),
        }
    gap_files = [
        {
            "symbol": r["symbol"],
            "kind": r["kind"],
            "month": r["month"],
            "geometry": r["geometry"],
            "ranges": r["interior_gap_ranges"],
        }
        for r in verified
        if r["interior_gap_ranges"]
    ]
    flags = Counter(flag for s in symbols for flag in s["review_flags"])
    summary = {
        "success": bool(reconciled and not errors),
        "reconciliation": reconciliation,
        "verified_raw_files": len(verified),
        "integrity_error_count": len(errors),
        "verified_raw_bytes": sum(r["bytes"] for r in verified),
        "symbol_count": len(symbols),
        "hourly_file_geometry": dict(geometry),
        "by_kind": by_kind,
        "constant_zero_volume_trade_files": sum(
            r["quality"]["zero_volume_constant_trade_artifact"] for r in verified
        ),
        "symbols_by_review_flag": dict(flags),
        "interior_gap_hours_trade_and_mark": sum(
            sum(g["missing_hours"] for g in r["interior_gap_ranges"]) for r in verified
        ),
        "historical_eligible_universe_ready": False,
        "meaning": "raw integrity and diagnostic audit only; not strategy eligibility",
    }
    for name, value in (
        ("summary.json", summary),
        ("integrity_errors.json", errors),
        ("symbol_quality.json", symbols),
        ("interior_gaps.json", gap_files),
    ):
        write_json(args.output_dir / name, value)
    if summary["success"]:
        write_review_rollup(args.output_dir, args.census_dir, args.download_dir)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary["success"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census-dir", type=Path, required=True)
    parser.add_argument("--download-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()
    with (
        exclusive_run(args.output_dir / ".run.lock"),
        exclusive_run(args.data_root / "raw/binance_um_universe/.download.lock"),
    ):
        raise SystemExit(0 if run(args) else 1)
