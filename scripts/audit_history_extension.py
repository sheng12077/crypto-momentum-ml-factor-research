"""Offline integrity, gap geometry and observed funding schedule audit of early RAW data."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import time
import traceback
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stderr, redirect_stdout
from itertools import pairwise
from pathlib import Path

from acquire_usdm_universe import (
    audit_rows,
    bind_run,
    digest,
    exclusive_run,
    read_json,
    validate_file_record,
    verify_payload,
    write_json,
)
from audit_usdm_acquisition import gap_geometry, read_gap_ranges
from check_universe_feasibility import month_range
from collect_cmc_weekly import LogTee

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parents[1] / "data"
SOURCE = ROOT / "data/interim/usdm_universe/history_extension_20261118"
OUTPUT = ROOT / "data/interim/usdm_universe/early_history_audit_20261119"
HOUR = 3600000


def resolve_raw(row, data_root):
    filename = validate_file_record(row)
    own = data_root / "raw/binance_um_universe" / row["kind"] / row["symbol"] / filename
    old_kind = {"trade": "perpetual_bars", "mark": "mark_bars", "funding": "funding"}[row["kind"]]
    legacy = data_root / "raw/binance_core" / f"{row['symbol'][:-4].lower()}_{old_kind}" / filename
    for candidate in (own, legacy):
        if candidate.exists():
            if not candidate.resolve().is_relative_to((data_root / "raw").resolve()):
                raise ValueError("raw cache resolves outside shared root")
            return candidate
    raise ValueError("no expected local raw cache; never trust another host's report path")


def csv_rows(body):
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        rows = list(
            csv.reader(io.StringIO(archive.read(archive.infolist()[0]).decode("utf-8-sig")))
        )
    if rows and rows[0][0] in ("calc_time", "funding_time", "open_time"):
        rows = rows[1:]
    return rows


def funding_events(rows):
    events = []
    for row in rows:
        if len(row) != 3:
            raise ValueError("unrecognized funding schema; no implicit column assumptions")
        stamp, interval, rate = int(row[0]), float(row[1]), float(row[2])
        if stamp >= 10**14 or stamp <= 0:
            raise ValueError("expected funding UTC millisecond timestamps")
        if not math.isfinite(interval) or interval <= 0 or not interval.is_integer():
            raise ValueError("funding interval must be positive integral hours")
        if not math.isfinite(rate):
            raise ValueError("funding rate must be finite")
        events.append(
            {"event_ms": stamp, "reported_interval_hours": int(interval), "rate_raw": row[2]}
        )
    return events


def schedule(events):
    events = sorted(events, key=lambda row: row["event_ms"])
    if len({row["event_ms"] for row in events}) != len(events):
        raise ValueError("duplicate funding events across partitions")
    changes, anomalies, jitter = [], [], 0
    for prior, current in pairwise(events):
        delta = current["event_ms"] - prior["event_ms"]
        offset = delta - prior["reported_interval_hours"] * HOUR
        detail = {
            "prior_ms": prior["event_ms"],
            "current_ms": current["event_ms"],
            "prior_reported_hours": prior["reported_interval_hours"],
            "current_reported_hours": current["reported_interval_hours"],
            "delta_ms": delta,
            "offset_from_prior_reported_interval_ms": offset,
        }
        if prior["reported_interval_hours"] != current["reported_interval_hours"]:
            changes.append(detail)
        elif abs(offset) > 1000:
            anomalies.append(detail)
        else:
            jitter = max(jitter, abs(offset))
    return {
        "events": len(events),
        "reported_interval_hours": sorted({r["reported_interval_hours"] for r in events}),
        "interval_changes": changes,
        "stable_interval_spacing_flags": anomalies,
        "maximum_small_spacing_offset_ms": jitter,
        "spacing_flags_are_not_proof_of_missing_settlements": True,
    }


def check_file(row, output):
    filename = validate_file_record(row)
    report_path = SOURCE / "download/files" / (digest(row["key"].encode()) + ".json")
    report_body = report_path.read_bytes()
    report = json.loads(report_body)
    if any(report[k] != row[k] for k in ("key", "symbol", "kind", "month")):
        raise ValueError("acquisition report/plan identity mismatch")
    if report["path"].replace("\\", "/").rsplit("/", 1)[-1] != filename:
        raise ValueError("acquisition report filename mismatch")
    raw = resolve_raw(row, DATA)
    body = raw.read_bytes()
    sha = verify_payload(
        body, raw.with_name(filename + ".CHECKSUM").read_bytes(), filename, row["size"]
    )
    metadata_body = raw.with_name(filename + ".metadata.json").read_bytes()
    metadata = json.loads(metadata_body)
    url = "https://data.binance.vision/" + urllib.parse.quote(row["key"], safe="/")
    if (
        report["sha256"] != sha
        or report["bytes"] != len(body)
        or report["source_url"] != url
        or metadata["sha256"] != sha
        or metadata["byte_size"] != len(body)
        or metadata.get("archive_url", metadata.get("source_url")) != url
        or metadata["retrieved_at"] != report["retrieved_at"]
    ):
        raise ValueError("acquisition/raw provenance mismatch")
    quality = audit_rows(body, filename, row["kind"], row["month"])
    if quality != report["quality"]:
        raise ValueError("fresh CSV quality disagrees with acquisition")
    geometry = gap_geometry(quality, row["month"]) if row["kind"] != "funding" else None
    gaps = (
        read_gap_ranges(raw, quality["row_count"])
        if geometry and geometry["interior_missing"]
        else []
    )
    if geometry and sum(g["missing_hours"] for g in gaps) != geometry["interior_missing"]:
        raise ValueError("raw interior gaps disagree with geometry")
    parsed = csv_rows(body) if row["kind"] in ("funding", "mark") else []
    result = {
        "key": row["key"],
        "symbol": row["symbol"],
        "kind": row["kind"],
        "month": row["month"],
        "sha256": sha,
        "bytes": len(body),
        "report_sha256": digest(report_body),
        "metadata_sha256": digest(metadata_body),
        "quality": quality,
        "geometry": geometry,
        "interior_gap_ranges": gaps,
        "funding_events": funding_events(parsed) if row["kind"] == "funding" else [],
        "mark_bar_open_ms": [int(r[0]) for r in parsed] if row["kind"] == "mark" else [],
    }
    checkpoint = output / "files" / (digest(row["key"].encode()) + ".json")
    cached = checkpoint.exists()
    if cached and read_json(checkpoint) != result:
        raise ValueError("audit checkpoint conflict")
    if not cached:
        write_json(checkpoint, result)
    return result, cached


def run(args):
    output = OUTPUT / args.action
    if args.action == "summary":
        for kind in ("pilot", "full"):
            path = OUTPUT / kind / "summary.json"
            print(
                json.dumps({"path": str(path), **read_json(path)})
                if path.exists()
                else f"{path}: not run"
            )
        return
    started = time.monotonic()
    paths = {
        "plan": SOURCE / "inventory/download_plan.json",
        "inventory": SOURCE / "inventory/summary.json",
        "download": SOURCE / "download/summary.json",
        "download_config": SOURCE / "download/run_config.json",
    }
    bodies = {key: path.read_bytes() for key, path in paths.items()}
    inputs = {key: json.loads(body) for key, body in bodies.items()}
    plan = inputs["plan"]
    if (
        not inputs["download"]["success"]
        or inputs["download"]["errors"]
        or inputs["download"]["verified_files"] != 1526
        or inputs["download"]["verified_bytes"] != 24153565
        or inputs["inventory"]["plan_hashes"]["download_plan.json"] != digest(bodies["plan"])
        or inputs["download_config"]["plan_sha256"] != digest(bodies["plan"])
        or not plan["complete_census"]
        or plan["official_checksum_gaps"]
    ):
        raise ValueError("requires completed bound early-history acquisition")
    if len(plan["files"]) != 1526 or sum(r["size"] for r in plan["files"]) != 24153565:
        raise ValueError("registered corpus counts/bytes disagree")
    if len({r["key"] for r in plan["files"]}) != len(plan["files"]):
        raise ValueError("duplicate planned archive keys")
    for row in plan["files"]:
        if not "2019-01" <= row["month"] <= "2020-12":
            raise ValueError("archive outside extension window")
    files = [
        r for r in plan["files"] if args.action == "full" or r["symbol"] in ("BTCUSDT", "ETHUSDT")
    ]
    binding = {
        "sources": {key: digest(body) for key, body in bodies.items()},
        "selected_keys": [r["key"] for r in files],
        "script_sha256": digest(Path(__file__).read_bytes()),
        "dependencies": {
            name: digest((ROOT / "scripts" / name).read_bytes())
            for name in (
                "acquire_usdm_universe.py",
                "audit_usdm_acquisition.py",
                "check_lifecycle_rows.py",
                "check_universe_feasibility.py",
                "collect_cmc_weekly.py",
            )
        },
    }
    with exclusive_run(output / ".audit.lock"):
        bind_run(output, binding)
        results, hits = [], 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = [pool.submit(check_file, row, output) for row in files]
            for number, job in enumerate(as_completed(jobs), 1):
                result, cached = job.result()
                results.append(result)
                hits += int(cached)
                if number % 200 == 0 or number == len(files):
                    print(
                        f"early history audit {number}/{len(files)}; cache_hits={hits}", flush=True
                    )
        groups = defaultdict(list)
        for row in results:
            groups[row["symbol"]].append(row)
        funding = []
        for symbol, rows in sorted(groups.items()):
            events = [event for row in rows for event in row["funding_events"]]
            mark_hours = {stamp for row in rows for stamp in row["mark_bar_open_ms"]}
            missing_mark = [
                e["event_ms"] for e in events if e["event_ms"] // HOUR * HOUR not in mark_hours
            ]
            months = {
                kind: {r["month"] for r in rows if r["kind"] == kind}
                for kind in ("trade", "mark", "funding")
            }
            funding_months = sorted(months["funding"])
            interior = (
                sorted(set(month_range(funding_months[0], funding_months[-1])) - months["funding"])
                if funding_months
                else []
            )
            funding.append(
                {
                    "symbol": symbol,
                    **schedule(events),
                    "events_without_same_hour_mark_bar": missing_mark,
                    "funding_interior_archive_months_absent": interior,
                    "bar_archive_months_without_funding_archive": sorted(
                        (months["trade"] | months["mark"]) - months["funding"]
                    ),
                    "exact_funding_event_mark_prices_proven": False,
                }
            )
        gaps = [
            {k: r[k] for k in ("symbol", "kind", "month", "geometry", "interior_gap_ranges")}
            for r in results
            if r["geometry"] and r["geometry"]["classification"] != "complete"
        ]
        artifacts = [
            {"symbol": r["symbol"], "month": r["month"], "quality": r["quality"]}
            for r in results
            if r["quality"]["zero_volume_constant_trade_artifact"]
        ]
        write_json(
            output / "gap_files.json",
            sorted(gaps, key=lambda r: (r["symbol"], r["kind"], r["month"])),
        )
        write_json(output / "funding_review.json", funding)
        write_json(output / "zero_volume_artifacts.json", artifacts)
        summary = {
            "success": True,
            "errors": [],
            "full_scope": args.action == "full",
            "verified_raw_files": len(results),
            "verified_bytes": sum(r["bytes"] for r in results),
            "cache_hits": hits,
            "gap_file_classifications": dict(
                Counter(r["geometry"]["classification"] for r in results if r["geometry"])
            ),
            "interior_missing_hours_by_kind": {
                kind: sum(r["geometry"]["interior_missing"] for r in results if r["kind"] == kind)
                for kind in ("trade", "mark")
            },
            "zero_volume_constant_trade_files": len(artifacts),
            "funding_rows": sum(r["events"] for r in funding),
            "funding_interval_changes": sum(len(r["interval_changes"]) for r in funding),
            "funding_stable_interval_spacing_flags": sum(
                len(r["stable_interval_spacing_flags"]) for r in funding
            ),
            "funding_events_without_same_hour_mark_bar": sum(
                len(r["events_without_same_hour_mark_bar"]) for r in funding
            ),
            "funding_maximum_small_spacing_offset_ms": max(
                (r["maximum_small_spacing_offset_ms"] for r in funding), default=0
            ),
            "historical_eligible_universe_ready": False,
            "funding_cashflows_verified": False,
            "exact_funding_event_mark_prices_proven": False,
            "OOS_performance_inspected": False,
            "metadata_http_requests": 0,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        write_json(output / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pilot", "full", "summary"))
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    log = ROOT / "reports/acquisition" / f"early_history_audit_{args.action}_20261119.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    print("Log: " + str(log), flush=True)
    with (
        log.open("a", encoding="utf-8") as handle,
        redirect_stdout(LogTee(sys.stdout, handle)),
        redirect_stderr(LogTee(sys.stderr, handle)),
    ):
        try:
            run(args)
        except Exception:
            traceback.print_exc()
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
