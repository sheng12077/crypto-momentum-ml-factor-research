"""Resumable archive census and checksum-verified RAW acquisition, without signals."""

from __future__ import annotations

import argparse
import calendar
import csv
import fcntl
import hashlib
import io
import json
import math
import shutil
import sys
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from check_lifecycle_rows import parse_zip
from check_universe_feasibility import ROOTS, Discovery, summarize_files

KINDS = ("trade", "mark", "funding")
SCHEMA = 1


@contextmanager
def exclusive_run(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(f"another acquisition process holds {path}") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def cancellable_pool(workers: int):
    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        yield pool
    finally:
        # Ctrl-C must not wait for tens of thousands of queued HTTP requests.
        # Only already running requests may finish (40-second request timeout).
        pool.shutdown(wait=True, cancel_futures=True)


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def bind_run(output: Path, config: dict) -> None:
    path = output / "run_config.json"
    if path.exists():
        if read_json(path) != config:
            raise ValueError(
                "output belongs to a different configuration; use a new output directory"
            )
    else:
        write_json(path, config)


def choose_symbols(seed: dict, selection: str | None) -> list[str]:
    population = sorted(
        {
            symbol
            for kind in KINDS
            for symbol in seed["roots"][kind]["all_symbols"]
            if symbol.endswith("USDT")
        }
    )
    if any("/" in s or "\\" in s or ".." in s for s in population):
        raise ValueError("unsafe archive symbol")
    if selection:
        selected = set(selection.split(","))
        if selected - set(population):
            raise ValueError(
                f"identifiers not found in frozen roots: {sorted(selected - set(population))}"
            )
        population = [s for s in population if s in selected]
    return population


def census_job(output: Path, symbol: str, kind: str, present: bool) -> dict:
    task = output / "jobs" / digest(f"{symbol}:{kind}".encode())[:24]
    result_path = task / "result.json"
    if result_path.exists():
        previous = read_json(result_path)
        if previous.get("success"):
            if previous["symbol"] != symbol or previous["kind"] != kind:
                raise ValueError("job identifier collision")
            for record in previous["manifest"]:
                if digest((task / record["path"]).read_bytes()) != record["sha256"]:
                    raise ValueError(f"cached listing integrity failure: {symbol}/{kind}")
            return previous
    # Failed jobs may leave diagnostic responses. Keep each attempt immutable.
    attempt = task / datetime.now(UTC).strftime("attempt_%Y%m%dT%H%M%S%fZ")
    client = Discovery(attempt)
    result = {"symbol": symbol, "kind": kind, "success": False, "manifest": []}
    try:
        objects = []
        if present:
            prefix = ROOTS[kind] + symbol + "/" + ("" if kind == "funding" else "1h/")
            _, objects = client.listing("listing", prefix)
        result.update(success=True, coverage=summarize_files(symbol, kind, objects))
    except Exception as exc:
        result["error"] = str(exc)
    for record in client.manifest:
        result["manifest"].append(
            {**record, "path": str((attempt / record["path"]).relative_to(task))}
        )
    write_json(result_path, result)
    return result


def load_snapshot(seed_path: Path) -> dict:
    manifest = json.loads((seed_path.parent / "manifest.json").read_text())
    record = next(r for r in manifest if r["path"] == "responses/exchange_info.raw")
    body = (seed_path.parent / record["path"]).read_bytes()
    if digest(body) != record["sha256"]:
        raise ValueError("current metadata snapshot integrity failure")
    return {"records": {r["symbol"]: r for r in json.loads(body)["symbols"]}, "provenance": record}


def identity_record(
    symbol: str, seed: dict, seed_hash: str, coverage: dict, snapshot: dict | None = None
) -> dict:
    current = seed.get("current_inventory") or {}
    record = {
        "instrument_id": symbol,
        "identity_status": "unresolved_archived_identifier",
        "historical_contract_type": None,
        "historical_underlying": None,
        "historical_contract_multiplier": None,
        "historical_listing_at": None,
        "lifecycle_events": [],
        "strategy_eligible": False,
        "in_current_perpetual_snapshot": symbol in current.get("symbols", []),
        "snapshot_is_not_historical_evidence": True,
        "seed_summary_sha256": seed_hash,
        "archive_bounds_are_not_lifecycle_facts": True,
        "archive_bounds": {
            k: {f: coverage.get(k, {}).get(f) for f in ("first_month", "last_month")} for k in KINDS
        },
    }
    current_record = (snapshot or {}).get("records", {}).get(symbol)
    record["current_product_metadata"] = (
        None
        if current_record is None
        else {
            field: current_record.get(field)
            for field in (
                "contractType",
                "status",
                "underlyingType",
                "underlyingSubType",
                "baseAsset",
                "quoteAsset",
                "marginAsset",
                "onboardDate",
                "deliveryDate",
            )
        }
    )
    record["current_product_metadata_provenance"] = (snapshot or {}).get("provenance")
    record["current_noncoin_annotation"] = bool(
        current_record and current_record.get("underlyingType") not in (None, "COIN")
    )
    if symbol == "WAVESUSDT":
        record["lifecycle_events"].append(
            {
                "event": "official_automatic_settlement_and_delisting",
                "effective_at": "2024-06-11T09:00:00+00:00",
                "announcement_available_at": None,
                "source_url": "https://www.binance.com/en/support/announcement/detail/f65faeeefe07417a8b6dd2900ba8da7e",
                "evidence_status": "official_effective_time_verified_publication_timestamp_unresolved",
                "use": "audit reference; not a backdated tradable announcement feature",
            }
        )
    return record


def census(args: argparse.Namespace) -> bool:
    seed_bytes = args.seed_summary.read_bytes()
    seed, seed_hash = json.loads(seed_bytes), digest(seed_bytes)
    snapshot = load_snapshot(args.seed_summary)
    symbols = choose_symbols(seed, args.symbols)
    config = {
        "schema": SCHEMA,
        "operation": "census",
        "seed_sha256": seed_hash,
        "symbols": symbols,
        "window": ["2021-01", "2026-10"],
    }
    bind_run(args.output_dir, config)
    jobs = [(s, k, s in seed["roots"][k]["all_symbols"]) for s in symbols for k in KINDS]
    results, errors = {}, []
    with cancellable_pool(args.workers) as pool:
        pending = {pool.submit(census_job, args.output_dir, *job): job for job in jobs}
        for index, future in enumerate(as_completed(pending), 1):
            symbol, kind, _ = pending[future]
            try:
                result = future.result()
                results[(symbol, kind)] = result
                if not result["success"]:
                    errors.append({"symbol": symbol, "kind": kind, "error": result["error"]})
            except Exception as exc:
                errors.append({"symbol": symbol, "kind": kind, "error": str(exc)})
            if index % 100 == 0 or index == len(jobs):
                print(f"census jobs {index}/{len(jobs)}; errors={len(errors)}", flush=True)
    coverage_rows, identities, files = [], [], []
    checksum_gaps = []
    for symbol in symbols:
        coverage = {k: results.get((symbol, k), {}).get("coverage", {}) for k in KINDS}
        common = sorted(set.intersection(*(set(coverage[k].get("months", [])) for k in KINDS)))
        coverage_rows.append(
            {
                "instrument_id": symbol,
                "series": coverage,
                "common_month_count": len(common),
                "common_months": common,
            }
        )
        identities.append(identity_record(symbol, seed, seed_hash, coverage, snapshot))
        for kind in KINDS:
            for row in coverage[kind].get("files", []):
                record = {**row, "symbol": symbol, "kind": kind}
                if row["has_checksum"]:
                    files.append(record)
                else:
                    checksum_gaps.append(record)
    files.sort(key=lambda row: (row["symbol"], row["kind"], row["month"]))
    plan = {
        "schema": SCHEMA,
        "window": config["window"],
        "seed_sha256": seed_hash,
        "complete_census": not errors,
        "official_checksum_gaps": len(checksum_gaps),
        "purpose": "raw research superset; not a tradable universe",
        "files": files,
    }
    requests = [m for r in results.values() for m in r["manifest"]]
    summary = {
        "success": not errors,
        "symbol_count": len(symbols),
        "listing_jobs": len(jobs),
        "errors": errors,
        "files_with_checksum": len(files),
        "checksum_gaps": len(checksum_gaps),
        "compressed_bytes": sum(row["size"] for row in files),
        "symbols_with_three_series_overlap": sum(
            r["common_month_count"] > 0 for r in coverage_rows
        ),
        "metadata_response_bytes": sum(r["bytes"] for r in requests),
        "metadata_requests_in_evidence": len(requests),
        "raw_acquisition_plan_ready": not errors and not checksum_gaps,
        "historical_eligible_universe_ready": False,
        "market_zip_downloads": 0,
        "current_noncoin_annotated_symbols": sum(
            r["current_noncoin_annotation"] for r in identities
        ),
        "symbols_without_current_metadata": sum(
            r["current_product_metadata"] is None for r in identities
        ),
        "snapshot_sha256": snapshot["provenance"]["sha256"],
    }
    for name, value in (
        ("coverage.json", coverage_rows),
        ("identity_ledger.json", identities),
        ("download_plan.json", plan),
        ("checksum_gaps.json", checksum_gaps),
        ("summary.json", summary),
    ):
        write_json(args.output_dir / name, value)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    return summary["success"]


def filter_plan(plan: dict, symbols: str | None, months: str | None) -> list[dict]:
    if not plan.get("complete_census") or plan.get("official_checksum_gaps"):
        raise ValueError("requires a complete census with no official-checksum gaps")
    files = plan["files"]
    if symbols:
        wanted = set(symbols.split(","))
        if wanted - {r["symbol"] for r in files}:
            raise ValueError("requested symbols absent from plan")
        files = [r for r in files if r["symbol"] in wanted]
    if months:
        wanted_months = set(months.split(","))
        for month in wanted_months:
            parsed = datetime.strptime(month, "%Y-%m")
            if parsed.strftime("%Y-%m") != month or not "2021-01" <= month <= "2026-10":
                raise ValueError("invalid requested months")
        files = [r for r in files if r["month"] in wanted_months]
    if not files:
        raise ValueError("empty download selection")
    keys = [r["key"] for r in files]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate archive keys")
    return files


def validate_file_record(row: dict) -> str:
    symbol, kind, month = row["symbol"], row["kind"], row["month"]
    if kind not in KINDS or not symbol.endswith("USDT"):
        raise ValueError("unexpected product or series")
    if any(x in symbol for x in ("/", "\\", "..")):
        raise ValueError("unsafe symbol")
    name = "fundingRate" if kind == "funding" else "1h"
    filename = f"{symbol}-{name}-{month}.zip"
    expected = ROOTS[kind] + symbol + "/" + ("" if kind == "funding" else "1h/") + filename
    if row["key"] != expected or not row["has_checksum"]:
        raise ValueError("unexpected archive key or missing checksum")
    if not 0 < row["size"] <= 8 * 1024 * 1024:
        raise ValueError("archive outside 8 MiB per-file budget")
    return filename


def verify_payload(body: bytes, checksum: bytes, filename: str, expected_size: int) -> str:
    record = checksum.decode().split()
    if len(record) != 2 or record[1].lstrip("*") != filename:
        raise ValueError("unexpected official checksum record")
    sha = digest(body)
    if sha != record[0] or len(body) != expected_size:
        raise ValueError("checksum or census-size mismatch; retain evidence and investigate")
    return sha


def audit_rows(body: bytes, filename: str, kind: str, month: str) -> dict:
    quality = parse_zip(body, filename[:-4] + ".csv", kind)
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        text = archive.read(archive.infolist()[0]).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    if rows and rows[0][0] in ("open_time", "calc_time", "funding_time"):
        rows = rows[1:]
    outside, bad_ohlc, off_grid = 0, 0, 0
    for row in rows:
        stamp = int(row[0])
        timestamp = datetime.fromtimestamp(stamp / (1_000_000 if stamp >= 10**14 else 1000), UTC)
        outside += int(timestamp.strftime("%Y-%m") != month)
        if kind != "funding":
            opening, high, low, close = map(float, row[1:5])
            bad_ohlc += int(high < max(opening, low, close) or low > min(opening, high, close))
            off_grid += int(
                timestamp.minute != 0 or timestamp.second != 0 or timestamp.microsecond != 0
            )
    if outside or bad_ohlc or off_grid:
        raise ValueError(
            f"structural violations: outside-month={outside}, OHLC={bad_ohlc}, grid={off_grid}"
        )
    quality["expected_hourly_rows"] = (
        None if kind == "funding" else calendar.monthrange(*map(int, month.split("-")))[1] * 24
    )
    quality["missing_hourly_rows"] = (
        None
        if kind == "funding"
        else max(0, quality["expected_hourly_rows"] - quality["row_count"])
    )
    quality["zero_volume_constant_trade_artifact"] = (
        kind == "trade"
        and quality["row_count"] > 0
        and quality["positive_volume_rows"] == 0
        and quality["constant_single_price"]
    )
    quality["strategy_eligible"] = False
    return quality


def acquire_file(row: dict, data_root: Path, output: Path) -> dict:
    filename = validate_file_record(row)
    symbol, kind = row["symbol"], row["kind"]
    own = data_root / "raw/binance_um_universe" / kind / symbol / filename
    old_kind = {"trade": "perpetual_bars", "mark": "mark_bars", "funding": "funding"}[kind]
    old = data_root / "raw/binance_core" / f"{symbol[:-4].lower()}_{old_kind}" / filename
    url = "https://data.binance.vision/" + urllib.parse.quote(row["key"], safe="/")
    location, reused = own, False
    for candidate in (own, old):
        if candidate.exists():
            checksum = candidate.with_name(filename + ".CHECKSUM").read_bytes()
            metadata = read_json(candidate.with_name(filename + ".metadata.json"))
            body = candidate.read_bytes()
            sha = verify_payload(body, checksum, filename, row["size"])
            source = metadata.get("archive_url", metadata.get("source_url"))
            if metadata.get("sha256") != sha or source != url or not metadata.get("retrieved_at"):
                raise ValueError("cached provenance mismatch")
            location, reused = candidate, True
            break
    else:
        request_dir = output / "requests" / digest(row["key"].encode())[:24]
        attempt = request_dir / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        client = Discovery(attempt)
        try:
            checksum = client.get("checksum", url + ".CHECKSUM", 4096)
            body = client.get("archive", url, 8 * 1024 * 1024)
        finally:
            write_json(attempt / "manifest.json", client.manifest)
        sha = verify_payload(body, checksum, filename, row["size"])
        metadata = {
            "source_url": url,
            "archive_url": url,
            "sha256": sha,
            "byte_size": len(body),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "checksum_url": url + ".CHECKSUM",
        }
        own.parent.mkdir(parents=True, exist_ok=True)
        # Metadata is published last. A partial cache fails closed on the next run.
        for path, payload in ((own, body), (own.with_name(filename + ".CHECKSUM"), checksum)):
            temporary = path.with_name(path.name + ".part")
            temporary.write_bytes(payload)
            temporary.replace(path)
        write_json(own.with_name(filename + ".metadata.json"), metadata)
    quality = audit_rows(body, filename, kind, row["month"])
    # The request evidence already retains a copy; own is the stable shared raw cache.
    result = {
        "symbol": symbol,
        "kind": kind,
        "month": row["month"],
        "key": row["key"],
        "path": str(location),
        "sha256": sha,
        "bytes": len(body),
        "cache_hit": reused,
        "source_url": url,
        "retrieved_at": metadata["retrieved_at"],
        "quality": quality,
    }
    write_json(output / "files" / (digest(row["key"].encode()) + ".json"), result)
    return result


def download(args: argparse.Namespace) -> bool:
    plan_body = args.plan.read_bytes()
    files = filter_plan(json.loads(plan_body), args.symbols, args.months)
    missing_requested = []
    if args.symbols and args.months:
        available = {(r["symbol"], r["kind"], r["month"]) for r in files}
        missing_requested = [
            {"symbol": symbol, "kind": kind, "month": month}
            for symbol in sorted(set(args.symbols.split(",")))
            for kind in KINDS
            for month in sorted(set(args.months.split(",")))
            if (symbol, kind, month) not in available
        ]
        if missing_requested:
            print(
                f"unavailable requested combinations: {json.dumps(missing_requested)}", flush=True
            )
    for row in files:
        validate_file_record(row)
    total = sum(r["size"] for r in files)
    if not math.isfinite(args.max_gib) or args.max_gib <= 0 or total > args.max_gib * 1024**3:
        raise ValueError(
            f"selection is {total} compressed bytes, outside explicit --max-gib budget"
        )
    args.data_root.mkdir(parents=True, exist_ok=True)
    # Request evidence retains raw bytes as well as the shared cache.
    if shutil.disk_usage(args.data_root).free < total * 2.2 + len(files) * 16384 + 256 * 1024**2:
        raise ValueError("insufficient free disk for raw cache and acquisition evidence")
    bind_run(
        args.output_dir,
        {
            "schema": SCHEMA,
            "operation": "download",
            "plan_sha256": digest(plan_body),
            "symbols": args.symbols,
            "months": args.months,
            "data_root": str(args.data_root.resolve()),
        },
    )
    results, errors = [], []
    with cancellable_pool(args.workers) as pool:
        pending = {
            pool.submit(acquire_file, row, args.data_root, args.output_dir): row for row in files
        }
        for index, future in enumerate(as_completed(pending), 1):
            try:
                results.append(future.result())
            except Exception as exc:
                row = pending[future]
                errors.append({"key": row["key"], "error": str(exc)})
                print(f"ERROR {row['key']}: {exc}", flush=True)
            if index % 100 == 0 or index == len(files):
                print(f"acquisition {index}/{len(files)}; errors={len(errors)}", flush=True)
    summary = {
        "success": not errors and len(results) == len(files),
        "planned_files": len(files),
        "verified_files": len(results),
        "unavailable_requested_combinations": missing_requested,
        "requested_selection_complete": not missing_requested,
        "cache_hits": sum(r["cache_hit"] for r in results),
        "downloaded_files": sum(not r["cache_hit"] for r in results),
        "errors": errors,
        "planned_compressed_bytes": total,
        "verified_bytes": sum(r["bytes"] for r in results),
        "zero_volume_constant_trade_files": sum(
            r["quality"]["zero_volume_constant_trade_artifact"] for r in results
        ),
        "files_with_missing_hours": sum(bool(r["quality"]["missing_hourly_rows"]) for r in results),
        "empty_files": sum(r["quality"]["row_count"] == 0 for r in results),
        "files_with_nonpositive_prices": sum(
            bool(r["quality"]["nonpositive_ohlc_rows"]) for r in results
        ),
        "historical_eligible_universe_ready": False,
        "meaning": "RAW acquisition success only; lifecycle/eligibility unresolved",
    }
    write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    return summary["success"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    census_parser = sub.add_parser("census")
    census_parser.add_argument("--seed-summary", type=Path, required=True)
    download_parser = sub.add_parser("download")
    download_parser.add_argument("--plan", type=Path, required=True)
    download_parser.add_argument("--data-root", type=Path, required=True)
    download_parser.add_argument("--months")
    download_parser.add_argument("--max-gib", type=float, required=True)
    for command in (census_parser, download_parser):
        command.add_argument("--output-dir", type=Path, required=True)
        command.add_argument("--symbols")
        command.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()
    try:
        with ExitStack() as stack:
            stack.enter_context(exclusive_run(args.output_dir / ".run.lock"))
            if args.operation == "download":
                stack.enter_context(
                    exclusive_run(args.data_root / "raw/binance_um_universe/.download.lock")
                )
            success = census(args) if args.operation == "census" else download(args)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
