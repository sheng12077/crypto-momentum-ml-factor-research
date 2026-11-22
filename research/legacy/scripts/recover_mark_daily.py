"""Bounded official daily-mark fallback for an incomplete primary recovery."""

from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.parse
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from acquire_usdm_universe import (
    bind_run,
    digest,
    exclusive_run,
    read_json,
    verify_payload,
    write_json,
)
from reconcile_mark_gaps import HOUR, ProbeClient, parse_payload
from recover_mark_gaps import RateGate, SourceConflict, context_flags, validate_response


def stable_location(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    prefix = "//wsl.localhost/Ubuntu-24.04/"
    return "/" + value[len(prefix) :] if value.lower().startswith(prefix.lower()) else value


def parse_daily(body: bytes, filename: str, date: str) -> list[list]:
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        members = archive.infolist()
        if (
            len(members) != 1
            or members[0].filename != filename[:-4] + ".csv"
            or members[0].file_size > 10 * 1024**2
        ):
            raise ValueError("unexpected daily ZIP members or decompression size")
        text = archive.read(members[0]).decode("utf-8-sig")
    values = [r for r in csv.reader(io.StringIO(text)) if r and r[0] != "open_time"]
    stamps = [int(r[0]) for r in values]
    if stamps != sorted(set(stamps)):
        raise ValueError("daily archive duplicate/unordered timestamps")
    for row in values:
        if (
            len(row) < 12
            or datetime.fromtimestamp(int(row[0]) / 1000, UTC).strftime("%Y-%m-%d") != date
        ):
            raise ValueError("daily archive date/schema mismatch")
    start = int(datetime.fromisoformat(date).replace(tzinfo=UTC).timestamp() * 1000)
    parse_payload(
        json.dumps(values).encode(), filename.split("-1h-", 1)[0], start, start + 24 * HOUR - 1
    )
    return values


def day_keys(job: dict) -> list[tuple[str, str]]:
    first = datetime.fromtimestamp(job["prior_ms"] / 1000, UTC).replace(hour=0)
    final = datetime.fromtimestamp(job["next_ms"] / 1000, UTC).replace(hour=0)
    result = []
    while first <= final:
        result.append((job["symbol"], first.strftime("%Y-%m-%d")))
        first += timedelta(days=1)
    return result


def daily_source(symbol: str, date: str, output: Path, gate: RateGate, budget_left: int) -> dict:
    key = digest(f"{symbol}:{date}".encode())
    directory = output / "daily" / key
    checkpoint = directory / "result.json"
    filename = f"{symbol}-1h-{date}.zip"
    url = "https://data.binance.vision/" + urllib.parse.quote(
        f"data/futures/um/daily/markPriceKlines/{symbol}/1h/{filename}", safe="/"
    )
    result = {"symbol": symbol, "date": date, "success": False, "new_requests": 0}
    try:
        if checkpoint.exists() and (prior := read_json(checkpoint)).get("success"):
            for field in ("zip_path", "checksum_path"):
                if (
                    not (directory / prior[field].replace("\\", "/"))
                    .resolve()
                    .is_relative_to(directory.resolve())
                ):
                    raise ValueError("cached daily path escape")
            body = (directory / prior["zip_path"].replace("\\", "/")).read_bytes()
            checksum = (directory / prior["checksum_path"].replace("\\", "/")).read_bytes()
            verify_payload(body, checksum, filename, prior["zip_bytes"])
            if digest(body) != prior["source_sha256"] or prior["source_url"] != url:
                raise ValueError("cached daily source metadata mismatch")
            result = {**prior, "new_requests": 0, "cache_hit": True}
            result["zip_path"] = prior["zip_path"].replace("\\", "/")
            result["checksum_path"] = prior["checksum_path"].replace("\\", "/")
        else:
            attempt = directory / datetime.now(UTC).strftime("attempt_%Y%m%dT%H%M%S%fZ")
            client = ProbeClient(attempt)
            try:
                if budget_left <= 0:
                    raise ValueError("combined daily ZIP budget exhausted")
                gate.wait()
                result["new_requests"] += 1
                checksum = client.get("checksum", url + ".CHECKSUM", 4096)
                gate.wait()
                result["new_requests"] += 1
                body = client.get("archive", url, min(2 * 1024**2, budget_left))
            finally:
                write_json(attempt / "manifest.json", client.manifest)
            verify_payload(body, checksum, filename, len(body))
            zip_path = attempt / "responses/archive.raw"
            checksum_path = attempt / "responses/checksum.raw"
            result.update(
                source_url=url,
                source_sha256=digest(body),
                zip_bytes=len(body),
                source_retrieved_at=client.manifest[-1]["retrieved_at"],
                zip_path=zip_path.relative_to(directory).as_posix(),
                checksum_path=checksum_path.relative_to(directory).as_posix(),
                source_payload_path=stable_location(zip_path),
                cache_hit=False,
            )
        if len(body) > budget_left:
            raise ValueError("combined daily ZIP budget exceeded")
        values = parse_daily(body, filename, date)
        result.update(success=True, values=values)
    except Exception as exc:
        result.update(success=False, error=str(exc))
    write_json(checkpoint, result)
    return result


def fallback(args: argparse.Namespace) -> bool:
    primary = read_json(args.primary_dir / "summary.json")
    overlay_path = args.primary_dir / "mark_overlay.jsonl"
    plan_body = args.plan.read_bytes()
    if (
        not primary["full_scope"]
        or primary["source_conflicts"]
        or digest(overlay_path.read_bytes()) != primary["overlay_sha256"]
    ):
        raise ValueError("primary recovery is not a trustworthy full-scope input")
    if primary["plan_sha256"] != digest(plan_body):
        raise ValueError("primary plan mismatch")
    plan = json.loads(plan_body)
    accepted = {
        (r["symbol"], r["timestamp_ms"]): r
        for r in (
            json.loads(line) for line in overlay_path.read_text(encoding="utf-8").splitlines()
        )
    }
    targets = {(j["symbol"], t): j for j in plan["jobs"] for t in j["targets"]}
    if not accepted.keys() <= targets.keys():
        raise ValueError("primary overlay contains unplanned keys")
    pending = [
        j for j in plan["jobs"] if any((j["symbol"], t) not in accepted for t in j["targets"])
    ]
    files = sorted({key for j in pending for key in day_keys(j)})
    if len(files) > 200:
        raise ValueError("daily fallback exceeds registered file budget")
    bind_run(
        args.output_dir,
        {
            "schema": 1,
            "plan_sha256": digest(plan_body),
            "primary_overlay_sha256": primary["overlay_sha256"],
            "daily_files": [list(key) for key in files],
        },
    )
    gate, results, zip_bytes = RateGate(), {}, 0
    for index, (symbol, date) in enumerate(files, 1):
        result = daily_source(symbol, date, args.output_dir, gate, 50 * 1024**2 - zip_bytes)
        results[(symbol, date)] = result
        if result["success"]:
            zip_bytes += result["zip_bytes"]
        if index % 10 == 0 or index == len(files):
            print(
                f"daily fallback {index}/{len(files)}; unavailable={sum(not r['success'] for r in results.values())}",
                flush=True,
            )
    errors, conflicts = [], []
    for job in pending:
        sources = [results[key] for key in day_keys(job)]
        try:
            if any(not source["success"] for source in sources):
                raise ValueError("one or more official daily archives unavailable or invalid")
            raw_values = [
                row
                for source in sources
                for row in source["values"]
                if job["prior_ms"] <= int(row[0]) <= job["next_ms"]
            ]
            raw_values.sort(key=lambda r: int(r[0]))
            rows = validate_response(json.dumps(raw_values).encode(), job, accepted)
            by_date = {source["date"]: source for source in sources}
            for row in rows:
                key = (row["symbol"], row["timestamp_ms"])
                if key in accepted:
                    continue
                source = by_date[
                    datetime.fromtimestamp(row["timestamp_ms"] / 1000, UTC).strftime("%Y-%m-%d")
                ]
                accepted[key] = {
                    **row,
                    "source_kind": "verified_official_daily_archive",
                    **{
                        field: source[field]
                        for field in (
                            "source_url",
                            "source_sha256",
                            "source_payload_path",
                            "source_retrieved_at",
                        )
                    },
                }
        except SourceConflict as exc:
            conflicts.extend((job["symbol"], t) for t in exc.stamps)
            errors.append({"symbol": job["symbol"], "job_id": job["job_id"], "error": str(exc)})
        except Exception as exc:
            errors.append({"symbol": job["symbol"], "job_id": job["job_id"], "error": str(exc)})
    for key in conflicts:
        accepted.pop(key, None)
    rows = [context_flags(accepted[key], targets[key]) for key in sorted(accepted)]
    overlay = args.output_dir / "mark_overlay.jsonl"
    temporary = overlay.with_suffix(".jsonl.part")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(overlay)
    unresolved = [
        {"symbol": s, "timestamp_ms": t} for s, t in sorted(targets.keys() - accepted.keys())
    ]
    summary = {
        "success": not unresolved and not conflicts,
        "full_scope": True,
        "plan_sha256": digest(plan_body),
        "target_hours": len(targets),
        "verified_overlay_rows": len(rows),
        "unresolved_hours": len(unresolved),
        "source_conflicts": len(set(conflicts)),
        "primary_verified_rows": primary["verified_overlay_rows"],
        "additional_daily_rows": len(rows) - primary["verified_overlay_rows"],
        "daily_archives_planned": len(files),
        "daily_archives_verified": sum(r["success"] for r in results.values()),
        "new_HTTP_requests": sum(r["new_requests"] for r in results.values()),
        "zip_bytes": zip_bytes,
        "rows_after_known_lifecycle_end": sum(r["audit_after_known_lifecycle_end"] for r in rows),
        "rows_after_last_positive_trade": sum(r["audit_after_last_positive_trade"] for r in rows),
        "overlay_sha256": digest(overlay.read_bytes()),
        "canonical_modified": False,
        "historical_eligible_universe_ready": False,
    }
    for name, value in (
        ("summary.json", summary),
        ("errors.json", errors),
        ("unresolved.json", unresolved),
        ("conflicts.json", [{"symbol": s, "timestamp_ms": t} for s, t in sorted(set(conflicts))]),
    ):
        write_json(args.output_dir / name, value)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary["success"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--primary-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    with exclusive_run(args.output_dir / ".run.lock"):
        raise SystemExit(0 if fallback(args) else 1)
