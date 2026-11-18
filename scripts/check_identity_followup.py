"""Bounded official-source follow-up and BNX activity audit; no strategy outcomes."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import time
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from collect_cmc_weekly import Downloader, checked_source, raw_bytes
from review_contract_identity import article_text

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parents[1] / "data"
DEFAULT = ROOT / "data/interim/identity_followup_20261118"
LIMIT = 32 * 1024**2


def capture(config_path, output):
    config = read_json(config_path)
    specs = config["sources"]
    if len(specs) > 20 or len({s["id"] for s in specs}) != len(specs):
        raise ValueError("invalid source count/IDs")
    for spec in specs:
        url = urlsplit(spec["url"])
        if (
            url.scheme != "https"
            or url.hostname
            not in (
                "www.binance.com",
                "coinmarketcap.com",
                "fapi.binance.com",
                "data.binance.vision",
                "s3-ap-northeast-1.amazonaws.com",
            )
            or not re.fullmatch(r"[a-z0-9_]+", spec["id"])
        ):
            raise ValueError("unexpected source URL/ID")
        if url.hostname == "s3-ap-northeast-1.amazonaws.com" and url.path != "/data.binance.vision":
            raise ValueError("unexpected S3 bucket")
    paused = output / "access_pause.json"
    if paused.exists() and time.time() < read_json(paused)["not_before_epoch"]:
        raise ValueError("access cooldown active; do not retry")
    if raw_bytes(output) > LIMIT:
        raise ValueError("raw budget exceeded")
    downloader = Downloader(output, LIMIT)
    results, errors, unavailable = [], [], []
    for spec in specs:
        # Freeze terminal not-found evidence for this bounded review; do not keep
        # retrying a deleted page. Access-denied responses still stop the run.
        previous_missing, exhausted = [], []
        for path in (output / "raw/attempts" / spec["id"]).glob("*.json"):
            meta = read_json(path)
            if meta["status"] == 404 and meta["url"] == spec["url"]:
                body = path.with_suffix(".raw").read_bytes()
                if digest(body) != meta["sha256"] or len(body) != meta["bytes"]:
                    raise ValueError("not-found evidence integrity failure")
                previous_missing.append(meta)
            elif (
                meta["url"] == spec["url"]
                and meta.get("attempt") == 3
                and (meta["status"] == 0 or meta["status"] >= 500)
            ):
                if digest(path.with_suffix(".raw").read_bytes()) != meta["sha256"]:
                    raise ValueError("failure evidence integrity failure")
                exhausted.append(meta)
        if previous_missing:
            unavailable.append({"id": spec["id"], "status": 404, "evidence": previous_missing[-1]})
            continue
        if exhausted:
            errors.append(
                {
                    "id": spec["id"],
                    "error": "three failed attempts frozen for this review round; not retried",
                }
            )
            continue
        try:
            _, meta, cached = downloader.get(spec["id"], spec["url"])
            results.append({"id": spec["id"], "source": meta, "cache_hit": cached})
        except Exception as exc:
            errors.append({"id": spec["id"], "error": str(exc)})
            if "HTTP 404" not in str(exc):
                break
            unavailable.append({"id": spec["id"], "status": 404})
    summary = {
        "success": len(results) == len(specs),
        "verified_sources": len(results),
        "requested_sources": len(specs),
        "http_requests": downloader.requests,
        "raw_bytes": raw_bytes(output),
        "results": results,
        "errors": errors,
        "unavailable_sources": unavailable,
        "config_sha256": digest(config_path.read_bytes()),
    }
    write_json(output / "capture_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, sort_keys=True))


def iso(stamp):
    return datetime.fromtimestamp(stamp / 1000, UTC).isoformat()


def parse_cmc_identity(body):
    text = body.decode("utf-8")
    found = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if found is None:
        raise ValueError("CMC identity payload missing")
    page = json.loads(found.group(1))
    detail = page["props"]["pageProps"]["detailRes"]["detail"]
    if type(detail["id"]) is not int or detail["id"] <= 0 or not detail["name"]:
        raise ValueError("invalid CMC identity")
    platforms = detail.get("platforms") or []
    if isinstance(platforms, dict):
        platforms = [platforms]
    return {key: detail[key] for key in ("id", "name", "symbol", "slug")} | {
        "contracts": [
            {
                key: p.get(key)
                for key in (
                    "contractAddress",
                    "contractPlatform",
                    "contractExplorerUrl",
                    "contractDecimals",
                )
            }
            for p in platforms
        ],
        "historical_content_version_proven": False,
    }


def activity_stats(rows, closure_ms):
    stamps = [int(r[0]) for r in rows]
    if len(stamps) != len(set(stamps)) or stamps != sorted(stamps):
        raise ValueError("duplicate/nonmonotonic bar times")
    positive = [int(r[0]) for r in rows if Decimal(r[5]) > 0]
    after = [r for r in rows if int(r[0]) >= closure_ms]
    return {
        "rows": len(rows),
        "first_open": iso(stamps[0]) if stamps else None,
        "last_open": iso(stamps[-1]) if stamps else None,
        "positive_volume_rows": len(positive),
        "zero_volume_rows": len(rows) - len(positive),
        "first_positive_open": iso(positive[0]) if positive else None,
        "last_positive_open": iso(positive[-1]) if positive else None,
        "constant_ohlc_tuple_count": len({tuple(r[1:5]) for r in rows}),
        "distinct_price_strings": len({p for r in rows for p in r[1:5]}),
        "rows_opening_at_or_after_captured_close": len(after),
        "positive_volume_rows_at_or_after_close": sum(Decimal(r[5]) > 0 for r in after),
        "closure_boundary_bar_is_not_proven_executable": True,
    }


def verify_bnx_month(kind, month, closure_ms):
    import pyarrow.parquet as pq

    name = f"BNXUSDT-1h-{month}.zip"
    raw = SHARED / "raw/binance_um_universe" / kind / "BNXUSDT" / name
    body = raw.read_bytes()
    meta = read_json(raw.with_suffix(".zip.metadata.json"))
    if meta["sha256"] != digest(body) or meta["byte_size"] != len(body):
        raise ValueError("raw metadata integrity failure")
    checksum = raw.with_suffix(".zip.CHECKSUM").read_text().split()
    if checksum != [digest(body), name]:
        raise ValueError("official checksum mismatch")
    key = urlsplit(meta["source_url"]).path.lstrip("/")
    release = SHARED / "canonical/binance_um_research/v20261117_001"
    index_path = release / "index" / (digest(key.encode()) + ".json")
    index = read_json(index_path)
    parquet = release / index["relative_path"]
    if index["raw_sha256"] != digest(body) or index["parquet_sha256"] != digest(
        parquet.read_bytes()
    ):
        raise ValueError("normalized provenance mismatch")
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        if archive.namelist() != [name.removesuffix(".zip") + ".csv"]:
            raise ValueError("unexpected ZIP member")
        if archive.infolist()[0].file_size > 10 * 1024**2:
            raise ValueError("uncompressed budget exceeded")
        rows = list(
            csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode("utf-8-sig")))
        )
    if rows and rows[0][0] == "open_time":
        rows = rows[1:]
    table = pq.read_table(str(parquet), columns=["bar_open_ms"], use_threads=False)
    if table["bar_open_ms"].to_pylist() != [int(r[0]) for r in rows] or index["rows"] != len(rows):
        raise ValueError("raw/normalized timestamps/count mismatch")
    return {
        "kind": kind,
        "volume_interpretation": "trade_quantity"
        if kind == "trade"
        else "placeholder_not_activity",
        "month": month,
        "raw_sha256": digest(body),
        "index_sha256": digest(index_path.read_bytes()),
        "source_url": meta["source_url"],
        **activity_stats(rows, closure_ms),
    }


def audit(config_path, output):
    closure = int(datetime(2025, 3, 17, 9, tzinfo=UTC).timestamp() * 1000)
    selected = [
        ("trade", "2023-01"),
        ("trade", "2023-02"),
        ("trade", "2025-03"),
        ("trade", "2025-04"),
        ("trade", "2026-10"),
        ("mark", "2025-04"),
        ("mark", "2026-10"),
    ]
    bnx = [verify_bnx_month(kind, month, closure) for kind, month in selected]
    specs = read_json(config_path)["sources"]
    sources = {}
    for spec in specs:
        cached = checked_source(output, spec["id"], spec["url"])
        if cached is None:
            continue
        body, meta, _ = cached
        item = {"source": meta}
        if spec["id"] == "sun_launch":
            _, text = article_text(body, "adac46dd47b142aebfa1c003c17af568")
            expected = ["SUNUSDT", "2024-08-22 13:05", "SunToken"]
            if not all(term in text for term in expected):
                raise ValueError("SUN launch assertion failed")
            item["launch_assertion_verified"] = True
        elif spec["id"] == "bnx_legacy_listing":
            import xml.etree.ElementTree as ET

            tree = ET.fromstring(body)
            item["listed_keys"] = [n.text for n in tree.iter() if n.tag.endswith("}Key")]
            item["empty_listing_is_not_proof_REST_history_missing"] = True
        elif spec["id"] == "bnx_legacy_bar":
            payload = json.loads(body)
            item["returned_bar_times"] = (
                [iso(int(r[0])) for r in payload] if isinstance(payload, list) else []
            )
            item["not_full_legacy_history_verification"] = True
        elif spec["id"] == "bnx_legacy_feb_checksum":
            item["checksum_record"] = body.decode().strip()
        elif spec["id"] == "bnx_legacy_feb_zip":
            checksum_spec = next(s for s in specs if s["id"] == "bnx_legacy_feb_checksum")
            checksum_body, _, _ = checked_source(output, checksum_spec["id"], checksum_spec["url"])
            name = "BNXUSDTSETTLED-1h-2023-02.zip"
            if checksum_body.decode().split() != [digest(body), name]:
                raise ValueError("legacy archive checksum mismatch")
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                if (
                    archive.namelist() != [name.removesuffix(".zip") + ".csv"]
                    or archive.infolist()[0].file_size > 10 * 1024**2
                ):
                    raise ValueError("unexpected legacy ZIP")
                rows = list(
                    csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode("utf-8-sig")))
                )
            if rows and rows[0][0] == "open_time":
                rows = rows[1:]
            old_close = int(datetime(2023, 2, 11, 4, tzinfo=UTC).timestamp() * 1000)
            item["legacy_activity"] = activity_stats(rows, old_close)
            item["not_integrated_into_existing_release"] = True
        else:
            text = body.decode("utf-8")
            # Identity strings/addresses only; no current prices, returns or ranks.
            item["sun_full_contract_address_present"] = "TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S" in text
            item["sats_same_asset_notice_present"] = "same asset in different denominations" in text
            item["no_historical_vintage_certification"] = True
            item["identity"] = parse_cmc_identity(body)
        sources[spec["id"]] = item
    config = {
        "tool_sha256": digest(Path(__file__).read_bytes()),
        "source_config_sha256": digest(config_path.read_bytes()),
        "verified_source_hashes": {k: v["source"]["sha256"] for k, v in sources.items()},
        "bnx_raw_hashes": [b["raw_sha256"] for b in bnx],
    }
    derived = output / "audit_003"
    bind_run(derived, config)
    write_json(derived / "bnx_quality.json", bnx)
    write_json(derived / "source_assertions.json", sources)
    result = {
        "success": True,
        "errors": [],
        "bnx_partitions_verified": len(bnx),
        "cached_sources_verified": len(sources),
        "strategy_and_OOS_performance_inspected": False,
        "historical_joins_approved": 0,
    }
    write_json(derived / "summary.json", result)
    print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["capture", "audit"])
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/identity_followup_sources_20261118.json"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT)
    args = parser.parse_args()
    with exclusive_run(args.output / ".followup.lock"):
        (capture if args.action == "capture" else audit)(args.config, args.output)


if __name__ == "__main__":
    main()
