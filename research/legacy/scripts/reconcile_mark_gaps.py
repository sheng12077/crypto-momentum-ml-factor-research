"""Validate existing mark backfills and make bounded public recovery probes."""

from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.error
import urllib.parse
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from acquire_usdm_universe import digest, exclusive_run, read_json, write_json
from check_universe_feasibility import Discovery

HOUR = 3_600_000
FIELDS = ("open", "high", "low", "close")
WINDOWS = (("2021-07-24", 96), ("2022-10-02", 24), ("2023-02-24", 24), ("2026-06-29", 24))


def milliseconds(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def parse_ohlc(values: list) -> dict:
    prices = [Decimal(str(v)) for v in values]
    if len(prices) != 4 or any(not v.is_finite() or v <= 0 for v in prices):
        raise ValueError("nonpositive/nonfinite mark OHLC")
    opening, high, low, close = prices
    if high < max(opening, low, close) or low > min(opening, high, close):
        raise ValueError("invalid mark OHLC ordering")
    return dict(zip(FIELDS, (str(v) for v in prices), strict=True))


def parse_payload(body: bytes, symbol: str, start: int, end: int) -> list[dict]:
    payload = json.loads(body)
    if not isinstance(payload, list):
        raise ValueError("mark API did not return a list")
    rows, seen = [], set()
    for values in payload:
        if not isinstance(values, list) or len(values) < 12:
            raise ValueError("unexpected mark kline schema")
        stamp = int(values[0])
        if stamp % HOUR or not start <= stamp <= end or stamp in seen:
            raise ValueError("shifted, off-grid, duplicate or out-of-range timestamp")
        if int(values[6]) != stamp + HOUR - 1:
            raise ValueError("incorrect hourly close timestamp")
        if rows and stamp <= rows[-1]["timestamp_ms"]:
            raise ValueError("unordered mark response")
        seen.add(stamp)
        rows.append(
            {
                "symbol": symbol,
                "timestamp_ms": stamp,
                "timestamp": datetime.fromtimestamp(stamp / 1000, UTC).isoformat(),
                **parse_ohlc(values[1:5]),
            }
        )
    return rows


def same_prices(first: dict, second: dict) -> bool:
    return all(Decimal(str(first[field])) == Decimal(str(second[field])) for field in FIELDS)


def source_path(data_root: Path, value: str, allowed: Path) -> Path:
    relative = value.removeprefix("data/")
    path = (data_root / relative).resolve()
    if not path.is_relative_to(allowed.resolve()):
        raise ValueError("manifest path outside expected data directory")
    return path


def canonical_backfill_path(data_root: Path, value: str) -> Path:
    # Explicit legacy layout migration; never edit the recorded manifest.
    legacy = "data/interim/binance_core_audit/series/"
    if value.startswith(legacy):
        value = "canonical/binance_core_audit/series/" + value.removeprefix(legacy)
    return source_path(data_root, value, data_root / "canonical")


def check_parquet(path: Path, rows: list[dict], symbol: str) -> None:
    import polars as pl

    frame = pl.read_parquet(path)
    actual = frame.to_dicts()
    reference = {r["timestamp_ms"]: r for r in rows}
    observed = [milliseconds(r["timestamp"].astimezone(UTC)) for r in actual]
    if len(observed) != len(set(observed)) or set(observed) != set(reference):
        raise ValueError("canonical/raw key sets differ")
    for row, stamp in zip(actual, observed, strict=True):
        if row["instrument_id"] != symbol or not same_prices(row, reference[stamp]):
            raise ValueError("canonical/raw symbol or OHLC differs")
        if milliseconds(row["close_timestamp"].astimezone(UTC)) != stamp + HOUR - 1:
            raise ValueError("canonical hourly close time differs")


def existing_backfills(data_root: Path) -> tuple[list, list, list]:
    root = data_root / "raw/binance_mark_backfill"
    validated, manifests, errors = [], [], []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        path = directory / "manifest.json"
        if not path.exists():
            manifests.append(
                {
                    "directory": str(directory),
                    "status": "orphan_not_reused",
                    "json_files": len(list(directory.glob("*.json"))),
                }
            )
            continue
        manifest = read_json(path)
        symbol = manifest["symbol"]
        local, local_errors = [], []
        for record in manifest["artifacts"]:
            try:
                url = urllib.parse.urlparse(record["source_url"])
                query = urllib.parse.parse_qs(url.query)
                if (
                    url.scheme != "https"
                    or url.netloc != "fapi.binance.com"
                    or url.path != "/fapi/v1/markPriceKlines"
                ):
                    raise ValueError("unexpected backfill source")
                if any(len(v) != 1 for v in query.values()):
                    raise ValueError("ambiguous query parameters")
                if (
                    query["symbol"] != [symbol]
                    or query["interval"] != ["1h"]
                    or query["limit"] != ["1"]
                ):
                    raise ValueError("backfill query metadata mismatch")
                start, end = int(query["startTime"][0]), int(query["endTime"][0])
                if start % HOUR or end != start + HOUR - 1:
                    raise ValueError("backfill request is not one hour")
                raw = source_path(data_root, record["relative_path"], root)
                body = raw.read_bytes()
                if (
                    digest(body) != record["sha256"]
                    or len(body) != record["byte_size"]
                    or record["status_code"] != 200
                ):
                    raise ValueError("backfill response integrity/status mismatch")
                if utc(record["retrieved_at"]) < datetime.fromtimestamp((end + 1) / 1000, UTC):
                    raise ValueError("response acquired before historical bar closed")
                rows = parse_payload(body, symbol, start, end)
                if len(rows) != 1 or rows[0]["timestamp_ms"] != start:
                    raise ValueError("backfill is empty or shifted")
                local.extend(
                    {
                        **r,
                        "source_kind": "existing_verified_API",
                        "source_path": str(raw),
                        "source_sha256": record["sha256"],
                    }
                    for r in rows
                )
            except Exception as exc:
                local_errors.append(
                    {
                        "manifest": str(path),
                        "source": record.get("relative_path"),
                        "error": str(exc),
                    }
                )
        try:
            parquet = canonical_backfill_path(data_root, manifest["parquet_path"])
            check_parquet(parquet, local, symbol)
        except Exception as exc:
            local_errors.append({"manifest": str(path), "error": f"Parquet verification: {exc}"})
        manifests.append(
            {
                "directory": str(directory),
                "symbol": symbol,
                "rows": len(local),
                "status": "verified" if not local_errors else "failed",
                "manifest_sha256": digest(path.read_bytes()),
                "recorded_parquet_path": manifest["parquet_path"],
                "resolved_canonical_path": str(
                    canonical_backfill_path(data_root, manifest["parquet_path"])
                ),
            }
        )
        errors.extend(local_errors)
        if not local_errors:
            validated.extend(local)
    # A missing derived file still fails the gate; exact duplicate source evidence
    # is diagnostic only and does not silently recreate or relabel that file.
    signatures = {}
    for item in manifests:
        if item["status"] == "orphan_not_reused":
            continue
        saved = read_json(Path(item["directory"]) / "manifest.json")
        signatures[item["directory"]] = sorted(
            (r["source_url"], r["sha256"], r["byte_size"]) for r in saved["artifacts"]
        )
    for item in manifests:
        if item["status"] != "failed":
            continue
        item["exact_source_duplicate_of_verified_run"] = next(
            (
                peer["directory"]
                for peer in manifests
                if peer["status"] == "verified"
                and signatures.get(peer["directory"]) == signatures.get(item["directory"])
            ),
            None,
        )
    return validated, manifests, errors


def missing_keys(gap_file: Path) -> set[tuple[str, int]]:
    result = set()
    for row in read_json(gap_file):
        if row["kind"] != "mark":
            continue
        for gap in row["ranges"]:
            start = milliseconds(utc(gap["prior_observed"])) + HOUR
            end = milliseconds(utc(gap["next_observed"]))
            result.update((row["symbol"], stamp) for stamp in range(start, end, HOUR))
    return result


def boundary_rows(
    symbol: str, month: str, stamps: set[int], download_dir: Path, plan: dict
) -> dict:
    key = next(
        r["key"]
        for r in plan["files"]
        if r["symbol"] == symbol and r["kind"] == "mark" and r["month"] == month
    )
    report = read_json(download_dir / "files" / (digest(key.encode()) + ".json"))
    body = Path(report["path"]).read_bytes()
    if digest(body) != report["sha256"]:
        raise ValueError("monthly boundary source checksum changed")
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        text = archive.read(archive.infolist()[0]).decode("utf-8-sig")
    result = {}
    for row in csv.reader(io.StringIO(text)):
        if row[0] == "open_time":
            continue
        stamp = int(row[0])
        if stamp in stamps:
            result[stamp] = parse_ohlc(row[1:5])
    if set(result) != stamps:
        raise ValueError("original monthly boundary observations missing")
    return result


class ProbeClient(Discovery):
    def get(self, label: str, url: str, max_bytes: int = 1024 * 1024) -> bytes:
        try:
            return super().get(label, url, max_bytes)
        except urllib.error.HTTPError as exc:
            body = exc.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ValueError("oversize HTTP error response") from exc
            relative = f"responses/{label}_http_error.raw"
            (self.output / relative).write_bytes(body)
            self.manifest.append(
                {
                    "source_url": url,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "status": exc.code,
                    "bytes": len(body),
                    "sha256": digest(body),
                    "path": relative,
                }
            )
            raise


def run(args: argparse.Namespace) -> bool:
    if (args.output_dir / "summary.json").exists():
        raise ValueError("use a new output directory; probe evidence is immutable")
    client = ProbeClient(args.output_dir)
    reusable = {}
    if args.probe_evidence_dir:
        reusable = {
            r["source_url"]: r for r in read_json(args.probe_evidence_dir / "probe_manifest.json")
        }
    missing = missing_keys(args.audit_dir / "interior_gaps.json")
    old, manifests, errors = existing_backfills(args.data_root)
    plan = read_json(args.census_dir / "download_plan.json")
    candidates = {}
    conflicts = []

    def accept(row: dict) -> None:
        key = (row["symbol"], row["timestamp_ms"])
        if key not in missing:
            return
        if key in candidates and not same_prices(row, candidates[key]):
            conflicts.append(
                {"symbol": key[0], "timestamp_ms": key[1], "error": "sources disagree"}
            )
            return
        candidates.setdefault(key, row)

    for row in old:
        accept(row)
    existing_covered = len(candidates)
    probes = []
    specifications = [
        (symbol, date, length)
        for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT")
        for date, length in WINDOWS
    ]
    specifications.append(("WAVESUSDT", "2026-06-29", 24))
    for symbol, date, length in specifications:
        gap_start = milliseconds(datetime.fromisoformat(date).replace(tzinfo=UTC))
        gap_end = gap_start + length * HOUR
        start, end = gap_start - HOUR, gap_end + HOUR - 1
        probe = {
            "symbol": symbol,
            "date": date,
            "expected_gap_hours": length,
            "post_known_lifecycle_event": symbol == "WAVESUSDT",
            "accepted_gap_hours": 0,
            "audited_gap_hours_in_probe": sum(
                (symbol, stamp) in missing for stamp in range(gap_start, gap_end, HOUR)
            ),
        }
        try:
            bounds = boundary_rows(symbol, date[:7], {start, gap_end}, args.download_dir, plan)
            query = urllib.parse.urlencode(
                {
                    "symbol": symbol,
                    "interval": "1h",
                    "startTime": start,
                    "endTime": end,
                    "limit": length + 2,
                }
            )
            label = f"{symbol}_{date}"
            url = "https://fapi.binance.com/fapi/v1/markPriceKlines?" + query
            if args.probe_evidence_dir:
                record = reusable[url]
                saved = (args.probe_evidence_dir / record["path"]).resolve()
                if not saved.is_relative_to(args.probe_evidence_dir.resolve()):
                    raise ValueError("probe evidence path escapes its run")
                body = saved.read_bytes()
                if (
                    digest(body) != record["sha256"]
                    or len(body) != record["bytes"]
                    or record["status"] != 200
                ):
                    raise ValueError("reused probe evidence integrity failure")
                relative = f"responses/{label}.raw"
                (args.output_dir / relative).write_bytes(body)
                client.manifest.append({**record, "path": relative, "reused_from": str(saved)})
            else:
                body = client.get(label, url)
            rows = parse_payload(body, symbol, start, end)
            indexed = {r["timestamp_ms"]: r for r in rows}
            matches = set(bounds) <= set(indexed) and all(
                same_prices(indexed[t], bounds[t]) for t in bounds
            )
            probe.update(
                returned_rows=len(rows),
                boundary_agreement=matches,
                returned_gap_hours=sum(gap_start <= r["timestamp_ms"] < gap_end for r in rows),
            )
            if matches:
                for row in rows:
                    if (
                        gap_start <= row["timestamp_ms"] < gap_end
                        and (symbol, row["timestamp_ms"]) in missing
                    ):
                        accept(
                            {
                                **row,
                                "source_kind": "new_bounded_API_probe",
                                "source_url": url,
                                "source_sha256": digest(body),
                            }
                        )
                        probe["accepted_gap_hours"] += 1
            probe["status"] = (
                "complete"
                if matches and probe["returned_gap_hours"] == length
                else "partial_or_conflicting"
            )
        except Exception as exc:
            probe.update(status="failed", error=str(exc))
        probes.append(probe)
        print(
            f"probe {symbol} {date}: {probe['status']}; accepted={probe['accepted_gap_hours']}/{length}",
            flush=True,
        )
    for conflict in conflicts:
        candidates.pop((conflict["symbol"], conflict["timestamp_ms"]), None)
    summary = {
        "existing_backfill_integrity_passed": not errors and not conflicts,
        "existing_verified_rows": len(old),
        "raw_rows_validated_before_parquet_check": sum(r.get("rows", 0) for r in manifests),
        "fully_verified_canonical_runs": sum(r["status"] == "verified" for r in manifests),
        "failed_existing_runs": sum(r["status"] == "failed" for r in manifests),
        "legacy_failed_runs_with_identical_verified_source_peer": sum(
            bool(r.get("exact_source_duplicate_of_verified_run")) for r in manifests
        ),
        "existing_manifests": len(manifests),
        "existing_rows_covering_audited_gaps": existing_covered,
        "existing_errors": errors,
        "conflicts": conflicts,
        "audited_missing_mark_hours": len(missing),
        "bounded_API_requests": len(client.manifest),
        "new_API_requests": sum("reused_from" not in r for r in client.manifest),
        "reused_API_responses": sum("reused_from" in r for r in client.manifest),
        "complete_probes": sum(r["status"] == "complete" for r in probes),
        "total_probes": len(probes),
        "verified_candidate_gap_hours": len(candidates),
        "candidate_hours_after_known_WAVES_lifecycle": sum(
            r["symbol"] == "WAVESUSDT" and r["timestamp_ms"] >= 1718096400000
            for r in candidates.values()
        ),
        "remaining_uncovered_gap_hours": len(missing) - len(candidates),
        "canonical_modified": False,
        "historical_eligible_universe_ready": False,
        "daily_archive_fallback_executed": False,
    }
    for name, value in (
        ("summary.json", summary),
        ("existing_manifests.json", manifests),
        ("probe_results.json", probes),
        ("probe_manifest.json", client.manifest),
        (
            "verified_candidates.json",
            sorted(candidates.values(), key=lambda r: (r["symbol"], r["timestamp_ms"])),
        ),
    ):
        write_json(args.output_dir / name, value)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary["existing_backfill_integrity_passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--census-dir", type=Path, required=True)
    parser.add_argument("--download-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--probe-evidence-dir", type=Path)
    args = parser.parse_args()
    with (
        exclusive_run(args.output_dir / ".run.lock"),
        exclusive_run(args.data_root / "raw/binance_um_universe/.download.lock"),
    ):
        raise SystemExit(0 if run(args) else 1)
