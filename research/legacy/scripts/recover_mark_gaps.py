"""Resumable exact-key mark recovery and new versioned research overlays."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import math
import threading
import time
import urllib.parse
import zipfile
from concurrent.futures import as_completed
from datetime import UTC, datetime
from pathlib import Path

from acquire_usdm_universe import (
    bind_run,
    cancellable_pool,
    digest,
    exclusive_run,
    read_json,
    write_json,
)
from reconcile_mark_gaps import (
    HOUR,
    ProbeClient,
    milliseconds,
    parse_ohlc,
    parse_payload,
    same_prices,
    utc,
)


def make_plan(args: argparse.Namespace) -> None:
    gap_path = args.audit_dir / "interior_gaps.json"
    quality_path = args.audit_dir / "symbol_quality.json"
    quality = {r["symbol"]: r for r in read_json(quality_path)}
    census = read_json(args.census_dir / "download_plan.json")
    index = {(r["symbol"], r["month"]): r for r in census["files"] if r["kind"] == "mark"}
    jobs = []
    for gap in read_json(gap_path):
        if gap["kind"] != "mark":
            continue
        source = index[(gap["symbol"], gap["month"])]
        report = read_json(args.download_dir / "files" / (digest(source["key"].encode()) + ".json"))
        body = Path(report["path"]).read_bytes()
        if digest(body) != report["sha256"]:
            raise ValueError("original monthly mark source changed")
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            text = archive.read(archive.infolist()[0]).decode("utf-8-sig")
        observed = {int(r[0]): r for r in csv.reader(io.StringIO(text)) if r[0] != "open_time"}
        for interval in gap["ranges"]:
            start, end = (
                milliseconds(utc(interval["prior_observed"])),
                milliseconds(utc(interval["next_observed"])),
            )
            targets = list(range(start + HOUR, end, HOUR))
            if not 1 <= len(targets) <= 96 or len(targets) != interval["missing_hours"]:
                raise ValueError("gap outside registered range limits")
            if any(t in observed for t in targets):
                raise ValueError("target is already present in monthly archive")
            boundaries = {str(t): parse_ohlc(observed[t][1:5]) for t in (start, end)}
            context = quality[gap["symbol"]]
            job = {
                "symbol": gap["symbol"],
                "month": gap["month"],
                "prior_ms": start,
                "next_ms": end,
                "targets": targets,
                "boundaries": boundaries,
                "monthly_source_sha256": report["sha256"],
                "monthly_source_path": report["path"],
                "current_metadata": context["current_metadata"],
                "last_positive_trade_bar": context["last_positive_trade_bar"],
                "lifecycle_events": [c["event"] for c in context["lifecycle_event_checks"]],
            }
            job["job_id"] = digest(json.dumps(job, sort_keys=True).encode())
            jobs.append(job)
    jobs.sort(key=lambda r: (r["symbol"], r["prior_ms"]))
    plan = {
        "schema": 1,
        "kind": "mark_missing_key_recovery",
        "jobs": jobs,
        "target_hours": sum(len(j["targets"]) for j in jobs),
        "gap_file_sha256": digest(gap_path.read_bytes()),
        "quality_sha256": digest(quality_path.read_bytes()),
        "seed_candidates_path": str(args.seed_candidates.resolve()),
        "seed_candidates_sha256": digest(args.seed_candidates.read_bytes()),
        "seed_probe_dir": str(args.seed_probe_dir.resolve()),
        "seed_probe_manifest_sha256": digest(
            (args.seed_probe_dir / "probe_manifest.json").read_bytes()
        ),
    }
    if args.output.exists():
        if read_json(args.output) != plan:
            raise ValueError("plan already exists with different contents")
    else:
        write_json(args.output, plan)
    print(
        json.dumps(
            {"plan": str(args.output), "ranges": len(jobs), "target_hours": plan["target_hours"]}
        ),
        flush=True,
    )


def verified_seeds(plan: dict) -> dict:
    path = Path(plan["seed_candidates_path"])
    if digest(path.read_bytes()) != plan["seed_candidates_sha256"]:
        raise ValueError("seed candidate index changed")
    probe_dir = Path(plan["seed_probe_dir"])
    manifest_path = probe_dir / "probe_manifest.json"
    if digest(manifest_path.read_bytes()) != plan["seed_probe_manifest_sha256"]:
        raise ValueError("seed probe manifest changed")
    probes = {r["source_url"]: r for r in read_json(manifest_path)}
    rows, payload_cache = {}, {}
    for candidate in read_json(path):
        if "source_path" in candidate:
            source = Path(candidate["source_path"])
            manifest = read_json(source.parent / "manifest.json")
            record = next(
                r for r in manifest["artifacts"] if r["sha256"] == candidate["source_sha256"]
            )
            url, acquired = record["source_url"], record["retrieved_at"]
            size, status = record["byte_size"], record["status_code"]
        else:
            url = candidate["source_url"]
            record = probes[url]
            source = (probe_dir / record["path"]).resolve()
            if not source.is_relative_to(probe_dir):
                raise ValueError("seed probe path escape")
            acquired, size, status = record["retrieved_at"], record["bytes"], record["status"]
        cache_key = (str(source), url)
        if cache_key not in payload_cache:
            body = source.read_bytes()
            if digest(body) != candidate["source_sha256"] or len(body) != size or status != 200:
                raise ValueError("seed raw source integrity failure")
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "fapi.binance.com"
                or parsed.path != "/fapi/v1/markPriceKlines"
            ):
                raise ValueError("unexpected seed endpoint")
            if query["symbol"] != [candidate["symbol"]] or query["interval"] != ["1h"]:
                raise ValueError("seed query mismatch")
            values = parse_payload(
                body, candidate["symbol"], int(query["startTime"][0]), int(query["endTime"][0])
            )
            payload_cache[cache_key] = {r["timestamp_ms"]: r for r in values}
        source_row = payload_cache[cache_key][candidate["timestamp_ms"]]
        if not same_prices(candidate, source_row):
            raise ValueError("seed candidate differs from its raw response")
        key = (candidate["symbol"], candidate["timestamp_ms"])
        if key in rows and not same_prices(rows[key], candidate):
            raise ValueError("conflicting seed candidates")
        if utc(acquired).timestamp() * 1000 < candidate["timestamp_ms"] + HOUR:
            raise ValueError("seed retrieved before bar completed")
        rows[key] = {
            **source_row,
            "source_kind": candidate["source_kind"],
            "source_url": url,
            "source_sha256": candidate["source_sha256"],
            "source_payload_path": str(source),
            "source_retrieved_at": acquired,
        }
    return rows


class SourceConflict(ValueError):
    def __init__(self, stamps: list[int]):
        super().__init__("new and existing source OHLC conflict")
        self.stamps = stamps


def validate_response(body: bytes, job: dict, seeds: dict) -> list[dict]:
    rows = parse_payload(body, job["symbol"], job["prior_ms"], job["next_ms"] + HOUR - 1)
    indexed = {r["timestamp_ms"]: r for r in rows}
    expected = set(range(job["prior_ms"], job["next_ms"] + HOUR, HOUR))
    if set(indexed) != expected:
        raise ValueError("partial response; complete range and both boundaries required")
    if not all(same_prices(indexed[int(t)], prices) for t, prices in job["boundaries"].items()):
        raise ValueError("API/monthly boundary OHLC conflict")
    conflicts = [
        t
        for t in job["targets"]
        if (job["symbol"], t) in seeds and not same_prices(indexed[t], seeds[(job["symbol"], t)])
    ]
    if conflicts:
        raise SourceConflict(conflicts)
    return [indexed[t] for t in job["targets"]]


class RateGate:
    def __init__(self):
        self.lock = threading.Lock()
        self.next_start = 0.0

    def wait(self) -> None:
        with self.lock:
            delay = self.next_start - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self.next_start = time.monotonic() + 0.25


def recover_job(job: dict, seeds: dict, output: Path, gate: RateGate) -> dict:
    if all((job["symbol"], t) in seeds for t in job["targets"]):
        return {"status": "seed", "job_id": job["job_id"], "rows": [], "new_requests": 0}
    directory = output / "jobs" / job["job_id"]
    checkpoint = directory / "result.json"
    query = urllib.parse.urlencode(
        {
            "symbol": job["symbol"],
            "interval": "1h",
            "startTime": job["prior_ms"],
            "endTime": job["next_ms"] + HOUR - 1,
            "limit": len(job["targets"]) + 2,
        }
    )
    url = "https://fapi.binance.com/fapi/v1/markPriceKlines?" + query
    result = {
        "status": "failed",
        "job_id": job["job_id"],
        "symbol": job["symbol"],
        "new_requests": 0,
    }
    try:
        if checkpoint.exists() and (previous := read_json(checkpoint)).get("status") == "complete":
            record = previous["source"]
            source = Path(record["payload_path"]).resolve()
            if not source.is_relative_to(directory.resolve()):
                raise ValueError("cached response path escape")
            body = source.read_bytes()
            if (
                digest(body) != record["sha256"]
                or len(body) != record["bytes"]
                or record["source_url"] != url
            ):
                raise ValueError("cached response integrity failure")
            rows = validate_response(body, job, seeds)
            source_kind = "verified_recovery_API"
            cached = True
        else:
            attempt = directory / datetime.now(UTC).strftime("attempt_%Y%m%dT%H%M%S%fZ")
            client = ProbeClient(attempt)
            gate.wait()
            result["new_requests"] = 1
            try:
                body = client.get("mark", url)
            finally:
                write_json(attempt / "manifest.json", client.manifest)
            record = {
                **client.manifest[-1],
                "payload_path": str((attempt / client.manifest[-1]["path"]).resolve()),
            }
            rows = validate_response(body, job, seeds)
            source_kind, cached = "verified_recovery_API", False
        accepted = [
            {
                **row,
                "source_kind": source_kind,
                "source_url": url,
                "source_sha256": record["sha256"],
                "source_payload_path": record["payload_path"],
                "source_retrieved_at": record["retrieved_at"],
            }
            for row in rows
        ]
        result.update(status="complete", source=record, rows=accepted, cache_hit=cached)
    except SourceConflict as exc:
        result.update(error=str(exc), conflicting_stamps=exc.stamps)
    except Exception as exc:
        result["error"] = str(exc)
    write_json(checkpoint, result)
    return result


def context_flags(row: dict, job: dict) -> dict:
    metadata = job["current_metadata"]
    known_ends = [milliseconds(utc(e["effective_at"])) for e in job["lifecycle_events"]]
    last = job["last_positive_trade_bar"]
    return {
        **row,
        "audit_after_known_lifecycle_end": any(row["timestamp_ms"] >= t for t in known_ends),
        "audit_after_last_positive_trade": bool(
            last and row["timestamp_ms"] > milliseconds(utc(last))
        ),
        "current_product_label": "unknown"
        if metadata is None
        else str(metadata.get("underlyingType")),
        "historical_strategy_eligible": False,
    }


def recover(args: argparse.Namespace) -> bool:
    plan_body = args.plan.read_bytes()
    plan, seeds = json.loads(plan_body), verified_seeds(json.loads(plan_body))
    jobs = plan["jobs"][: args.limit_ranges] if args.limit_ranges else plan["jobs"]
    bind_run(
        args.output_dir,
        {
            "schema": 1,
            "operation": "mark_recovery",
            "plan_sha256": digest(plan_body),
            "limit_ranges": args.limit_ranges,
        },
    )
    targets = {(j["symbol"], t): j for j in jobs for t in j["targets"]}
    accepted = {key: value for key, value in seeds.items() if key in targets}
    errors, conflicts, results = [], [], []
    gate = RateGate()
    with cancellable_pool(args.workers) as pool:
        pending = {pool.submit(recover_job, job, seeds, args.output_dir, gate): job for job in jobs}
        for index, future in enumerate(as_completed(pending), 1):
            job = pending[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "status": "failed",
                    "job_id": job["job_id"],
                    "error": str(exc),
                    "new_requests": 0,
                }
            results.append(result)
            if result["status"] == "failed":
                errors.append(
                    {"job_id": job["job_id"], "symbol": job["symbol"], "error": result["error"]}
                )
            for stamp in result.get("conflicting_stamps", []):
                conflicts.append((job["symbol"], stamp))
            for row in result.get("rows", []):
                key = (row["symbol"], row["timestamp_ms"])
                if key not in targets:
                    raise ValueError("attempted recovery outside frozen targets")
                if key in accepted and not same_prices(accepted[key], row):
                    conflicts.append(key)
                else:
                    accepted.setdefault(key, row)
            if index % 100 == 0 or index == len(jobs):
                print(f"mark recovery {index}/{len(jobs)}; failed={len(errors)}", flush=True)
    for key in conflicts:
        accepted.pop(key, None)
    rows = [context_flags(accepted[key], targets[key]) for key in sorted(accepted)]
    missing = [
        {"symbol": key[0], "timestamp_ms": key[1]}
        for key in sorted(targets.keys() - accepted.keys())
    ]
    overlay = args.output_dir / "mark_overlay.jsonl"
    temporary = overlay.with_suffix(".jsonl.part")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(overlay)
    summary = {
        "success": not errors and not conflicts and not missing,
        "full_scope": not bool(args.limit_ranges),
        "plan_sha256": digest(plan_body),
        "target_ranges": len(jobs),
        "target_hours": len(targets),
        "verified_overlay_rows": len(rows),
        "unresolved_hours": len(missing),
        "failed_jobs": len(errors),
        "source_conflicts": len(set(conflicts)),
        "new_API_requests": sum(r["new_requests"] for r in results),
        "cached_ranges": sum(r.get("cache_hit", False) for r in results),
        "seed_complete_ranges": sum(r["status"] == "seed" for r in results),
        "rows_after_known_lifecycle_end": sum(r["audit_after_known_lifecycle_end"] for r in rows),
        "rows_after_last_positive_trade": sum(r["audit_after_last_positive_trade"] for r in rows),
        "overlay_sha256": digest(overlay.read_bytes()),
        "canonical_modified": False,
        "historical_eligible_universe_ready": False,
    }
    for name, value in (
        ("summary.json", summary),
        ("errors.json", errors),
        ("unresolved.json", missing),
        ("conflicts.json", [{"symbol": s, "timestamp_ms": t} for s, t in sorted(set(conflicts))]),
    ):
        write_json(args.output_dir / name, value)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary["success"]


def export_overlay(args: argparse.Namespace) -> None:
    summary = read_json(args.recovery_dir / "summary.json")
    source = args.recovery_dir / "mark_overlay.jsonl"
    if (
        (not summary["success"] and not getattr(args, "allow_partial", False))
        or not summary["full_scope"]
        or summary.get("source_conflicts", 0)
        or digest(source.read_bytes()) != summary["overlay_sha256"]
    ):
        raise ValueError("requires a complete, unmodified full-scope recovery overlay")
    manifest_path = args.output_dir / "manifest.json"
    if args.output_dir.exists():
        raise ValueError("choose a new version directory; never overwrite a published overlay")
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if any(
            not math.isfinite(float(row[field])) or float(row[field]) <= 0
            for field in ("open", "high", "low", "close")
        ):
            raise ValueError("unsafe numeric price conversion")
    expected_rows = summary.get("verified_overlay_rows", summary["target_hours"])
    if len(rows) != expected_rows or len({(r["symbol"], r["timestamp_ms"]) for r in rows}) != len(
        rows
    ):
        raise ValueError("overlay row/key-set mismatch")
    args.output_dir.mkdir(parents=True)
    path = args.output_dir / "mark_gap_overlay.parquet"
    if importlib.util.find_spec("polars"):
        import polars as pl

        frame = (
            pl.DataFrame(rows)
            .with_columns(
                pl.from_epoch("timestamp_ms", time_unit="ms")
                .dt.replace_time_zone("UTC")
                .alias("timestamp"),
                pl.from_epoch(pl.col("timestamp_ms") + HOUR - 1, time_unit="ms")
                .dt.replace_time_zone("UTC")
                .alias("close_timestamp"),
                pl.col("symbol").alias("instrument_id"),
                *[
                    pl.col(field).alias(field + "_raw")
                    for field in ("open", "high", "low", "close")
                ],
            )
            .with_columns(
                *[pl.col(field).cast(pl.Float64) for field in ("open", "high", "low", "close")]
            )
        )
        frame.write_parquet(path)
        if not frame.equals(pl.read_parquet(path)):
            raise ValueError("Parquet roundtrip mismatch")
    else:
        import pyarrow as pa
        import pyarrow.parquet as pq

        records = []
        for row in rows:
            record = {
                **row,
                "instrument_id": row["symbol"],
                "timestamp": datetime.fromtimestamp(row["timestamp_ms"] / 1000, UTC),
                "close_timestamp": datetime.fromtimestamp(
                    (row["timestamp_ms"] + HOUR - 1) / 1000, UTC
                ),
            }
            for field in ("open", "high", "low", "close"):
                record[field + "_raw"], record[field] = row[field], float(row[field])
            records.append(record)
        table = pa.Table.from_pylist(records)
        schema = pa.schema(
            [
                pa.field(f.name, pa.timestamp("ms", tz="UTC"))
                if f.name in ("timestamp", "close_timestamp")
                else f
                for f in table.schema
            ]
        )
        table = table.cast(schema)
        pq.write_table(table, path)
        if not table.equals(pq.read_table(path)):
            raise ValueError("Parquet roundtrip mismatch")
    write_json(
        manifest_path,
        {
            "schema": "mark_gap_overlay_v1",
            "rows": len(rows),
            "recovery_complete": summary["success"],
            "unresolved_hours": summary.get("unresolved_hours", 0),
            "source_jsonl_sha256": summary["overlay_sha256"],
            "plan_sha256": summary["plan_sha256"],
            "parquet_sha256": digest(path.read_bytes()),
            "parquet": str(path.resolve()),
            "tool_sha256": digest(Path(__file__).read_bytes()),
            "historical_strategy_eligible": False,
            "merged_with_existing_canonical": False,
            "price_storage": "Float64 plus exact raw decimal string columns; volume not invented",
        },
    )
    print(json.dumps(read_json(manifest_path), sort_keys=True), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    prepare = sub.add_parser("plan")
    for name in (
        "audit-dir",
        "census-dir",
        "download-dir",
        "seed-candidates",
        "seed-probe-dir",
        "output",
    ):
        prepare.add_argument("--" + name, type=Path, required=True)
    acquire = sub.add_parser("run")
    acquire.add_argument("--plan", type=Path, required=True)
    acquire.add_argument("--output-dir", type=Path, required=True)
    acquire.add_argument("--limit-ranges", type=int)
    acquire.add_argument("--workers", type=int, choices=(1, 2), default=2)
    export = sub.add_parser("export")
    export.add_argument("--recovery-dir", type=Path, required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    export.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    if args.operation == "plan":
        make_plan(args)
    elif args.operation == "export":
        with exclusive_run(args.output_dir.parent / ".export.lock"):
            export_overlay(args)
    else:
        if args.limit_ranges is not None and args.limit_ranges < 1:
            parser.error("--limit-ranges must be positive")
        with exclusive_run(args.output_dir / ".run.lock"):
            raise SystemExit(0 if recover(args) else 1)


if __name__ == "__main__":
    main()
