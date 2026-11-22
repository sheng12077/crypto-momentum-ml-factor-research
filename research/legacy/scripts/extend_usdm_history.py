"""Inventory frozen early archive evidence and acquire a new, bounded RAW extension."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
import urllib.parse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

from acquire_usdm_universe import (
    KINDS,
    bind_run,
    choose_symbols,
    digest,
    download,
    exclusive_run,
    read_json,
    validate_file_record,
    write_json,
)
from check_universe_feasibility import ROOTS, S3, month_range, parse_listing
from collect_cmc_weekly import LogTee

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/usdm_universe"
CENSUS = BASE / "census_full_20261117"
SEED = ROOT / "data/interim/universe_feasibility/20261117_metadata_pilot"
OUTPUT = BASE / "history_extension_20261118"
DATA = ROOT.parents[1] / "data"


def job_objects(census: Path, symbol: str, kind: str, present: bool):
    job = census / "jobs" / digest(f"{symbol}:{kind}".encode())[:24]
    result_body = (job / "result.json").read_bytes()
    result = json.loads(result_body)
    if not result["success"] or result["symbol"] != symbol or result["kind"] != kind:
        raise ValueError("cached job failed or changed identity")
    records = result["manifest"]
    if bool(records) != present:
        raise ValueError("root membership/listing evidence mismatch")
    prefix = ROOTS[kind] + symbol + "/" + ("" if kind == "funding" else "1h/")
    objects, token, hashes = [], None, []
    for page, record in enumerate(records):
        parts = record["path"].replace("\\", "/").split("/")
        if any(part in ("", ".", "..") or ":" in part for part in parts):
            raise ValueError("unsafe cached evidence path")
        if not record["path"].endswith(f"responses/listing_{page:03d}.raw"):
            raise ValueError("listing pages missing or reordered")
        url = urllib.parse.urlsplit(record["source_url"])
        expected_url = urllib.parse.urlsplit(S3)
        query = urllib.parse.parse_qs(url.query)
        expected_query = {"list-type": ["2"], "prefix": [prefix]}
        if token is not None:
            expected_query["continuation-token"] = [token]
        if (url.scheme, url.netloc, url.path, url.fragment) != (
            expected_url.scheme,
            expected_url.netloc,
            expected_url.path,
            "",
        ) or query != expected_query:
            raise ValueError("listing URL/pagination mismatch")
        body = (job / record["path"]).read_bytes()
        if (
            record["status"] != 200
            or len(body) != record["bytes"]
            or digest(body) != record["sha256"]
        ):
            raise ValueError("cached listing integrity failure")
        prefixes, found, token = parse_listing(body)
        if prefixes or any(not row["key"].startswith(prefix) for row in found):
            raise ValueError("listing outside exact series prefix")
        if token is None and page + 1 != len(records):
            raise ValueError("extra listing pages after completion")
        objects.extend(found)
        hashes.append(record["sha256"])
    if token is not None:
        raise ValueError("incomplete listing pagination")
    if len({row["key"] for row in objects}) != len(objects):
        raise ValueError("duplicate archive object")
    return objects, {"result_sha256": digest(result_body), "listing_sha256": hashes}


def selected_files(symbol, kind, objects, start="2019-01", end="2026-10"):
    name = "fundingRate" if kind == "funding" else "1h"
    prefix = ROOTS[kind] + symbol + "/" + ("" if kind == "funding" else "1h/")
    pattern = re.compile(re.escape(prefix + symbol + "-" + name + "-") + r"(\d{4}-\d{2})\.zip")
    keys = {row["key"] for row in objects}
    files = []
    for item in objects:
        match = pattern.fullmatch(item["key"])
        if match and start <= match[1] <= end:
            month = match[1]
            if datetime.strptime(month, "%Y-%m").strftime("%Y-%m") != month:
                raise ValueError("invalid archive month")
            row = {
                **item,
                "symbol": symbol,
                "kind": kind,
                "month": month,
                "has_checksum": item["key"] + ".CHECKSUM" in keys,
            }
            validate_file_record({**row, "has_checksum": True})
            files.append(row)
    return sorted(files, key=lambda row: row["month"])


def pilot_files(files):
    chosen = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for kind in KINDS:
            available = [r for r in files if r["symbol"] == symbol and r["kind"] == kind]
            if available:
                chosen.append(min(available, key=lambda row: row["month"]))
    if not chosen or len(chosen) > 6 or sum(row["size"] for row in chosen) > 4 * 1024**2:
        raise ValueError("pilot absent or outside registered six-file/4MiB budget")
    return sorted(chosen, key=lambda row: (row["symbol"], row["kind"], row["month"]))


def verify_plan(directory, filename):
    summary = read_json(directory / "summary.json")
    body = (directory / filename).read_bytes()
    if not summary["success"] or not summary["raw_acquisition_plan_ready"]:
        raise ValueError("historical inventory is not acquisition-ready")
    if digest(body) != summary["plan_hashes"][filename]:
        raise ValueError("extension plan integrity failure")
    plan = json.loads(body)
    binding = read_json(directory / "run_config.json")
    if binding["script_sha256"] != digest(Path(__file__).read_bytes()):
        raise ValueError("inventory script changed; use a new registered version")
    for name, sha in binding["dependencies"].items():
        if digest((ROOT / "scripts" / name).read_bytes()) != sha:
            raise ValueError("inventory dependency changed")
    if plan["inventory_binding_sha256"] != digest(json.dumps(binding, sort_keys=True).encode()):
        raise ValueError("plan/source binding mismatch")
    if plan["window"] != ["2019-01", "2020-12"]:
        raise ValueError("extension scope changed")
    for row in plan["files"]:
        if not "2019-01" <= row["month"] <= "2020-12":
            raise ValueError("download outside historical extension")
        validate_file_record(row)


def inventory(output):
    started = time.monotonic()
    seed_body = (SEED / "summary.json").read_bytes()
    seed = json.loads(seed_body)
    config_body = (CENSUS / "run_config.json").read_bytes()
    config = json.loads(config_body)
    old_summary_body = (CENSUS / "summary.json").read_bytes()
    old_summary = json.loads(old_summary_body)
    names = choose_symbols(seed, None)
    if (
        config["seed_sha256"] != digest(seed_body)
        or config["symbols"] != names
        or len(names) != 924
        or old_summary["listing_jobs"] != 2772
        or not old_summary["success"]
        or old_summary["errors"]
    ):
        raise ValueError("frozen census population/configuration mismatch")
    source_manifest_body = (SEED / "manifest.json").read_bytes()
    root_hashes = []
    for record in json.loads(source_manifest_body):
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe seed evidence path")
        body = (SEED / relative).read_bytes()
        if (
            record["status"] != 200
            or digest(body) != record["sha256"]
            or len(body) != record["bytes"]
        ):
            raise ValueError("frozen root evidence integrity failure")
        root_hashes.append(record["sha256"])
    all_files, job_hashes, review, coverage = [], {}, [], []
    for number, symbol in enumerate(names, 1):
        series = {}
        for kind in KINDS:
            present = symbol in seed["roots"][kind]["all_symbols"]
            objects, binding = job_objects(CENSUS, symbol, kind, present)
            job_hashes[f"{symbol}:{kind}"] = binding
            series[kind] = selected_files(symbol, kind, objects)
            all_files.extend(series[kind])
        months = {kind: {row["month"] for row in rows} for kind, rows in series.items()}
        earlier = {
            kind: sorted(m for m in values if m <= "2020-12") for kind, values in months.items()
        }
        coverage.append(
            {
                "instrument_id": symbol,
                "series": {
                    kind: {
                        "months": values,
                        "first_month": values[0] if values else None,
                        "last_month": values[-1] if values else None,
                    }
                    for kind, values in earlier.items()
                },
                "common_archive_months": sorted(
                    set.intersection(*(set(v) for v in earlier.values()))
                ),
            }
        )
        absent_funding = sorted((months["trade"] | months["mark"]) - months["funding"])
        funding_only = sorted(months["funding"] - months["trade"] - months["mark"])
        if absent_funding or funding_only:
            review.append(
                {
                    "instrument_id": symbol,
                    "bar_months_without_funding_archive": absent_funding,
                    "funding_months_without_trade_or_mark_archive": funding_only,
                    "meaning": "archive mismatch review only; not proven missing or payable events",
                }
            )
        if number % 100 == 0 or number == len(names):
            print(f"cached history inventory {number}/{len(names)}", flush=True)
    files = [row for row in all_files if row["month"] <= "2020-12"]
    checksum_gaps = [row for row in files if not row["has_checksum"]]
    files.sort(key=lambda row: (row["symbol"], row["kind"], row["month"]))
    old_files = [row for row in all_files if row["month"] >= "2021-01" and row["has_checksum"]]
    if (
        len(old_files) != old_summary["files_with_checksum"]
        or sum(r["size"] for r in old_files) != old_summary["compressed_bytes"]
    ):
        raise ValueError("reparsed old-window totals disagree with frozen census")
    binding = {
        "seed_sha256": digest(seed_body),
        "seed_manifest_sha256": digest(source_manifest_body),
        "seed_evidence_hashes": root_hashes,
        "census_config_sha256": digest(config_body),
        "census_summary_sha256": digest(old_summary_body),
        "job_hashes": job_hashes,
        "extension_window": ["2019-01", "2020-12"],
        "script_sha256": digest(Path(__file__).read_bytes()),
        "dependencies": {
            name: digest((ROOT / "scripts" / name).read_bytes())
            for name in (
                "acquire_usdm_universe.py",
                "check_universe_feasibility.py",
                "check_lifecycle_rows.py",
            )
        },
    }
    bind_run(output, binding)
    plan = {
        "schema": 1,
        "window": ["2019-01", "2020-12"],
        "complete_census": True,
        "official_checksum_gaps": len(checksum_gaps),
        "inventory_binding_sha256": digest(json.dumps(binding, sort_keys=True).encode()),
        "purpose": "frozen archive raw superset, not a causal universe",
        "files": files,
    }
    write_json(output / "download_plan.json", plan)
    write_json(output / "coverage.json", coverage)
    write_json(output / "checksum_gaps.json", checksum_gaps)
    write_json(output / "funding_reconciliation_queue.json", review)
    monthly = []
    for month in month_range("2019-01", "2020-12"):
        members = {
            kind: {r["symbol"] for r in files if r["month"] == month and r["kind"] == kind}
            for kind in KINDS
        }
        monthly.append(
            {
                "month": month,
                "archive_identifiers_by_kind": {k: len(v) for k, v in members.items()},
                "three_series_archive_identifiers": len(set.intersection(*members.values())),
            }
        )
    write_json(output / "monthly_counts.json", monthly)
    pilot = {**plan, "files": pilot_files(files)}
    write_json(output / "pilot_plan.json", pilot)
    by_kind = {
        kind: {
            "files": sum(r["kind"] == kind for r in files),
            "first_month": min((r["month"] for r in files if r["kind"] == kind), default=None),
            "identifiers": len({r["symbol"] for r in files if r["kind"] == kind}),
        }
        for kind in KINDS
    }
    result = {
        "success": True,
        "errors": [],
        "identifiers_screened": len(names),
        "cached_jobs_verified": len(job_hashes),
        "window": plan["window"],
        "files": len(files),
        "compressed_bytes": sum(r["size"] for r in files),
        "series": by_kind,
        "checksum_gaps": len(checksum_gaps),
        "funding_review_identifiers": len(review),
        "metadata_http_requests": 0,
        "market_zip_downloads": 0,
        "raw_acquisition_plan_ready": bool(files) and not checksum_gaps,
        "plan_hashes": {
            name: digest((output / name).read_bytes())
            for name in ("download_plan.json", "pilot_plan.json")
        },
        "historical_eligible_universe_ready": False,
        "OOS_performance_inspected": False,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    write_json(output / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory", "pilot", "download", "summary"))
    parser.add_argument("--max-gib", type=float)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    if args.action == "download" and args.max_gib is None:
        parser.error("full download requires explicit --max-gib budget")
    log = ROOT / "reports/acquisition" / f"history_extension_{args.action}_20261118.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    print("Log: " + str(log), flush=True)
    with (
        log.open("a", encoding="utf-8") as handle,
        redirect_stdout(LogTee(sys.stdout, handle)),
        redirect_stderr(LogTee(sys.stderr, handle)),
    ):
        try:
            if args.action == "summary":
                for folder in ("inventory", "pilot", "download"):
                    path = OUTPUT / folder / "summary.json"
                    print(
                        json.dumps({"path": str(path), **read_json(path)})
                        if path.exists()
                        else f"{path}: not run"
                    )
                return
            if args.action == "inventory":
                with exclusive_run(OUTPUT / "inventory/.run.lock"):
                    inventory(OUTPUT / "inventory")
                return
            plan_name = "pilot_plan.json" if args.action == "pilot" else "download_plan.json"
            verify_plan(OUTPUT / "inventory", plan_name)
            run_args = argparse.Namespace(
                plan=OUTPUT / "inventory" / plan_name,
                data_root=DATA,
                output_dir=OUTPUT / args.action,
                symbols=None,
                months=None,
                max_gib=4 / 1024 if args.action == "pilot" else args.max_gib,
                workers=args.workers,
            )
            with ExitStack() as stack:
                stack.enter_context(exclusive_run(run_args.output_dir / ".run.lock"))
                stack.enter_context(exclusive_run(DATA / "raw/binance_um_universe/.download.lock"))
                if not download(run_args):
                    raise ValueError("RAW acquisition incomplete; inspect saved errors")
        except Exception:
            traceback.print_exc()
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
