"""Bounded research-input diagnostics; no factors, performance or eligible universe."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from acquire_usdm_universe import digest, exclusive_run, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parents[1] / "data"
METRIC = "CapMrktCurUSD"
PILOT_PARTITIONS = (
    ("BTCUSDT", "2021-01"),
    ("BTCUSDT", "2024-01"),
    ("ETHUSDT", "2021-01"),
    ("ETHUSDT", "2024-01"),
    ("WAVESUSDT", "2024-06"),
    ("LITUSDT", "2025-01"),
    ("LITUSDT", "2025-12"),
    ("PUMPUSDT", "2025-04"),
    ("PUMPUSDT", "2025-07"),
    ("MDTUSDT", "2024-05"),
    ("MDTUSDT", "2026-10"),
)


def fetch(url, directory, maximum=5 * 1024**2):
    identity = digest(url.encode())
    metadata = directory / (identity + ".json")
    raw = directory / (identity + ".raw")
    if metadata.exists():
        report = read_json(metadata)
        body = raw.read_bytes()
        if report["url"] != url or len(body) != report["bytes"] or digest(body) != report["sha256"]:
            raise ValueError("source cache integrity failure")
        return body, {**report, "cache_hit": True}
    request = urllib.request.Request(url, headers={"User-Agent": "research-input-readiness/1.0"})
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read(maximum + 1)
        if len(body) > maximum:
            raise ValueError("response exceeds diagnostic budget")
        report = {
            "url": url,
            "http_status": response.code,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "bytes": len(body),
            "sha256": digest(body),
            "content_type": response.headers.get("Content-Type"),
        }
    directory.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(body)
    write_json(metadata, report)
    return body, {**report, "cache_hit": False}


def parse_caps(payload, requested_assets, start, end):
    if payload.get("next_page_url"):
        raise ValueError("pilot response paginated; cannot claim complete")
    result, seen = [], set()
    start_dt, end_dt = (
        datetime.fromisoformat(start).replace(tzinfo=UTC),
        datetime.fromisoformat(end).replace(tzinfo=UTC),
    )
    for row in payload["data"]:
        asset, stamp = row["asset"], datetime.fromisoformat(row["time"].replace("Z", "+00:00"))
        if stamp.utcoffset() != timedelta(0):
            raise ValueError("daily source timestamp must be UTC")
        if asset not in requested_assets or not start_dt <= stamp <= end_dt:
            raise ValueError("unexpected asset or time")
        if stamp.hour or stamp.minute or stamp.second or stamp.microsecond:
            raise ValueError("unexpected daily label")
        key = asset, stamp
        if key in seen:
            raise ValueError("duplicate cap observation")
        seen.add(key)
        value = row.get(METRIC)
        if value is None:
            continue
        number = Decimal(value)
        if not number.is_finite() or number <= 0:
            raise ValueError("nonpositive/nonfinite market cap")
        result.append(
            {
                "vendor_asset_id": asset,
                "source_time_raw": row["time"],
                "market_cap_raw": value,
                "metric": METRIC,
                "historical_content_version_proven": False,
                "available_at": None,
            }
        )
    expected = {
        (asset, start_dt + timedelta(days=day))
        for asset in requested_assets
        for day in range((end_dt - start_dt).days + 1)
    }
    missing = sorted(
        (asset, stamp.isoformat())
        for asset, stamp in expected
        - {
            (
                r["vendor_asset_id"],
                datetime.fromisoformat(r["source_time_raw"].replace("Z", "+00:00")),
            )
            for r in result
        }
    )
    return result, missing


def parse_snapshot(body, date):
    """Extract only cap/identity fields, never performance fields from the page."""
    expected_title = "Historical Snapshot - " + datetime.strptime(date, "%Y%m%d").strftime(
        "%d %B %Y"
    )
    if expected_title not in body.decode("utf-8"):
        raise ValueError("snapshot date/title mismatch")
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', body.decode("utf-8"), re.S)
    if match is None:
        raise ValueError("public snapshot has no structured payload")
    page = json.loads(match.group(1))
    state = json.loads(page["props"]["initialState"], parse_float=Decimal)
    rows = state["cryptocurrency"]["listingHistorical"]["data"]
    if not rows:
        raise ValueError("snapshot empty")
    end = datetime.strptime(date, "%Y%m%d").replace(tzinfo=UTC) + timedelta(days=1)
    result, seen = [], set()
    for row in rows:
        identity = row["id"]
        if identity in seen:
            raise ValueError("duplicate snapshot asset id")
        seen.add(identity)
        quote = row["quote"]["USD"]
        updated = quote["lastUpdated"]
        if datetime.fromisoformat(updated.replace("Z", "+00:00")) >= end:
            raise ValueError("snapshot contains observations after requested day")
        cap = Decimal(str(quote["marketCap"]))
        if not cap.is_finite() or cap <= 0:
            raise ValueError("invalid snapshot market cap")
        result.append(
            {
                "vendor_asset_id": identity,
                "name": row["name"],
                "symbol": row["symbol"],
                "slug": row["slug"],
                "snapshot_date": date,
                "source_updated_at_raw": updated,
                "market_cap_decimal": str(cap),
                "circulating_supply_decimal": str(row["circulatingSupply"]),
                "historical_content_version_proven": False,
                "available_at": None,
                "mapping_status": "unverified",
            }
        )
    return result


def funding_stats(table, identity):
    rows = table.to_pylist()
    seen, offsets, intervals = set(), [], Counter()
    after = 0
    endings = [
        datetime.fromisoformat(e["effective_at"])
        for e in identity["official_events"]
        if e["event_type"] == "automatic_settlement"
    ]
    launches = [
        datetime.fromisoformat(e["effective_at"])
        for e in identity["official_events"]
        if e["event_type"] == "launch"
    ]
    for row in rows:
        stamp = row["event_timestamp_ms"]
        if stamp in seen:
            raise ValueError("duplicate funding event")
        seen.add(stamp)
        hours = row["funding_interval_hours"]
        if not isinstance(hours, int) or hours <= 0:
            raise ValueError("invalid source interval")
        rate = Decimal(row["funding_rate_raw"])
        if not rate.is_finite():
            raise ValueError("invalid funding rate")
        step = hours * 3_600_000
        residue = stamp % step
        offsets.append(min(residue, step - residue))
        intervals[hours] += 1
        moment = datetime.fromtimestamp(stamp / 1000, UTC)
        last_end = max((end for end in endings if end <= moment), default=None)
        # Ex-post audit context only; absence of a later captured launch is NOT proof of inactivity.
        if last_end is not None and not any(last_end < launch <= moment for launch in launches):
            after += 1
    return {
        "rows": len(rows),
        "source_interval_hours_counts": dict(intervals),
        "exact_interval_boundary_rows": sum(x == 0 for x in offsets),
        "within_1000ms_boundary_rows": sum(x <= 1000 for x in offsets),
        "max_nearest_boundary_distance_ms": max(offsets, default=None),
        "after_captured_settlement_without_captured_relaunch_ex_post": after,
        "funding_cashflows_verified": False,
        "timestamps_modified": False,
    }


def run(args):
    import pyarrow.parquet as pq

    def load_funding(symbol, month):
        key = f"data/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"
        index = read_json(args.release / "index" / (digest(key.encode()) + ".json"))
        path = args.release / "observations/funding" / symbol / (month + ".parquet")
        if digest(path.read_bytes()) != index["parquet_sha256"]:
            raise ValueError("release funding partition integrity failure")
        table = pq.read_table(path)
        if table.num_rows != index["rows"]:
            raise ValueError("release funding row count mismatch")
        return table

    release = read_json(args.release / "manifest.json")
    if not release["success"] or not release["full_scope"]:
        raise ValueError("requires completed full observation release")
    summary, sources, errors = {}, [], []
    base = "https://community-api.coinmetrics.io/v4"
    url = base + "/catalog/asset-metrics?metrics=" + METRIC
    body, provenance = fetch(url, args.output_dir / "responses")
    sources.append(provenance)
    if provenance["http_status"] != 200:
        raise ValueError("public cap catalogue unavailable")
    catalog = json.loads(body)
    assets = {
        asset
        for metric in catalog["data"]
        for frequency in metric["frequencies"]
        if frequency["frequency"] == "1d"
        for asset in frequency["assets"]
    }
    lifecycle_summary = read_json(args.lifecycle_dir / "summary.json")
    if (
        not lifecycle_summary["success"]
        or digest((args.lifecycle_dir / "identity_ledger.json").read_bytes())
        != lifecycle_summary["ledger_sha256"]
        or digest((args.lifecycle_dir / "events.json").read_bytes())
        != lifecycle_summary["events_sha256"]
    ):
        raise ValueError("lifecycle evidence integrity failure")
    ledger = read_json(args.lifecycle_dir / "identity_ledger.json")
    review = []
    for row in ledger:
        symbol = row["instrument_id"]
        base_asset = (row.get("current_product_metadata") or {}).get("baseAsset")
        candidates = sorted(
            asset
            for asset in assets
            if base_asset
            and (asset == base_asset.lower() or asset.startswith(base_asset.lower() + "_"))
        )
        review.append(
            {
                "instrument_id": symbol,
                "current_base_annotation": base_asset,
                "lexical_candidates_only": candidates,
                "mapping_status": "unverified",
                "known_identity_reuse": row["known_identity_reuse"],
                "historical_strategy_eligible": False,
            }
        )
    cap_rows, cap_missing = [], []
    for start, end in (("2021-01-01", "2021-01-08"), ("2024-01-01", "2024-01-08")):
        url = (
            base
            + f"/timeseries/asset-metrics?assets=btc,eth&metrics={METRIC}&frequency=1d&start_time={start}&end_time={end}&page_size=100"
        )
        try:
            body, provenance = fetch(url, args.output_dir / "responses")
            sources.append(provenance)
            if provenance["http_status"] != 200:
                raise ValueError("pilot history HTTP " + str(provenance["http_status"]))
            parsed, missing = parse_caps(json.loads(body), {"btc", "eth"}, start, end)
            cap_rows += [{**row, "source": provenance} for row in parsed]
            cap_missing += missing
        except Exception as exc:
            errors.append({"stage": "market_cap_pilot", "error": str(exc)})
    write_json(args.output_dir / "market_cap_pilot.json", cap_rows)
    write_json(args.output_dir / "market_cap_mapping_review.json", review)
    summary["market_cap"] = {
        "vendor": "Coin Metrics Community",
        "metric": METRIC,
        "definition": "current issued supply times daily USD close; not interchangeable with circulating/free-float cap",
        "catalog_daily_assets": len(assets),
        "identifiers_reviewed": len(review),
        "identifiers_with_lexical_candidates": sum(
            bool(r["lexical_candidates_only"]) for r in review
        ),
        "approved_historical_mappings": 0,
        "pilot_rows": len(cap_rows),
        "pilot_missing_keys": cap_missing,
        "pilot_expected_rows": 32,
        "point_in_time_ready": False,
        "full_history_acquired": False,
    }
    snapshot_rows = []
    probe_reports = []
    for date in ("20210103", "20240107"):
        try:
            body, provenance = fetch(
                "https://coinmarketcap.com/historical/" + date + "/", args.output_dir / "responses"
            )
            sources.append(provenance)
            if provenance["http_status"] != 200:
                probe_reports.append({"date": date, "http_status": provenance["http_status"]})
                continue
            parsed = parse_snapshot(body, date)
            snapshot_rows += [{**row, "source": provenance} for row in parsed]
            probe_reports.append({"date": date, "rows": len(parsed), "http_status": 200})
        except Exception as exc:
            probe_reports.append({"date": date, "error": str(exc)})
            errors.append({"stage": "cmc_snapshot", "date": date, "error": str(exc)})
    for item in review:
        token = item["current_base_annotation"] or item["instrument_id"].removesuffix("USDT")
        matches = [row for row in snapshot_rows if row["symbol"].casefold() == token.casefold()]
        item["cmc_snapshot_lexical_candidates_only"] = [
            {key: row[key] for key in ("vendor_asset_id", "name", "symbol", "snapshot_date")}
            for row in matches
        ]
    write_json(args.output_dir / "market_cap_mapping_review.json", review)
    write_json(args.output_dir / "cmc_snapshot_pilot.json", snapshot_rows)
    summary["cmc_public_snapshots"] = {
        "probes": probe_reports,
        "rows": len(snapshot_rows),
        "access_path": "public historical webpage, no login/API bypass",
        "coverage_limit": "first page only; 200 ranked assets observed per sampled date",
        "point_in_time_ready": False,
        "bulk_acquisition_done": False,
        "approved_historical_mappings": 0,
        "identifiers_with_lexical_candidates": sum(
            bool(r["cmc_snapshot_lexical_candidates_only"]) for r in review
        ),
    }
    access = []
    for vendor, url in (
        (
            "CoinGecko unauthenticated historical API",
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range?vs_currency=usd&from=1609459200&to=1610064000",
        ),
        (
            "CoinPaprika keyless historical API",
            "https://api.coinpaprika.com/v1/tickers/btc-bitcoin/historical?start=2021-01-01&end=2021-01-08&interval=1d",
        ),
    ):
        try:
            _, provenance = fetch(url, args.output_dir / "responses")
            sources.append(provenance)
            access.append(
                {
                    "vendor": vendor,
                    "http_status": provenance["http_status"],
                    "interpretation": "access probe only; HTTP status is not an entitlement determination",
                }
            )
        except Exception as exc:
            access.append({"vendor": vendor, "error": str(exc)})
    summary["other_access_probes"] = access
    fund_results = []
    by_symbol = {row["instrument_id"]: row for row in ledger}
    for symbol, month in PILOT_PARTITIONS:
        path = args.release / "observations/funding" / symbol / (month + ".parquet")
        if not path.exists():
            errors.append(
                {
                    "stage": "funding_pilot",
                    "symbol": symbol,
                    "month": month,
                    "error": "partition absent; not zero funding",
                }
            )
            continue
        table = load_funding(symbol, month)
        fund_results.append(
            {
                "symbol": symbol,
                "month": month,
                "parquet_sha256": digest(path.read_bytes()),
                **funding_stats(table, by_symbol[symbol]),
            }
        )
    write_json(args.output_dir / "funding_pilot.json", fund_results)
    summary["funding"] = {
        "pilot_partitions": len(fund_results),
        "planned_partitions": len(PILOT_PARTITIONS),
        "rows": sum(r["rows"] for r in fund_results),
        "max_nearest_boundary_distance_ms": max(
            (r["max_nearest_boundary_distance_ms"] or 0) for r in fund_results
        ),
        "after_captured_settlement_without_captured_relaunch_ex_post": sum(
            r["after_captured_settlement_without_captured_relaunch_ex_post"] for r in fund_results
        ),
        "cashflow_ready": False,
        "exact_settlement_prices_available_from_hourly_OHLC": False,
    }
    reconciliations = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&startTime=1609459200000&endTime=1609631999999&limit=100"
        try:
            body, provenance = fetch(url, args.output_dir / "responses")
            sources.append(provenance)
            if provenance["http_status"] != 200:
                reconciliations.append(
                    {
                        "symbol": symbol,
                        "http_status": provenance["http_status"],
                        "status": "unresolved_access",
                    }
                )
                continue
            api_rows = json.loads(body)
            if not isinstance(api_rows, list) or len(api_rows) >= 100:
                raise ValueError("unexpected or possibly truncated API pilot")
            archived = load_funding(symbol, "2021-01").to_pylist()
            archived = {
                r["event_timestamp_ms"]: r["funding_rate_raw"]
                for r in archived
                if 1609459200000 <= r["event_timestamp_ms"] <= 1609631999999
            }
            seen, mismatches = set(), []
            marked = 0
            for row in api_rows:
                stamp = row["fundingTime"]
                if (
                    row["symbol"] != symbol
                    or stamp in seen
                    or not 1609459200000 <= stamp <= 1609631999999
                ):
                    raise ValueError("unexpected/duplicate API funding key")
                seen.add(stamp)
                if stamp not in archived or Decimal(row["fundingRate"]) != Decimal(archived[stamp]):
                    mismatches.append(stamp)
                mark = row.get("markPrice")
                if mark:
                    number = Decimal(mark)
                    if not number.is_finite() or number <= 0:
                        raise ValueError("invalid API-associated mark price")
                    marked += 1
            missing = sorted(set(archived) - seen)
            reconciliations.append(
                {
                    "symbol": symbol,
                    "api_rows": len(api_rows),
                    "archive_rows": len(archived),
                    "exact_key_and_rate_mismatches": mismatches,
                    "archive_keys_absent_from_API": missing,
                    "api_rows_with_positive_associated_mark_price": marked,
                    "status": "matched"
                    if not mismatches and not missing and seen
                    else "unresolved_conflict",
                    "interpretation": "ex-post funding history; not a historical forecast or proof of publication time",
                }
            )
        except Exception as exc:
            reconciliations.append({"symbol": symbol, "status": "unresolved", "error": str(exc)})
    write_json(args.output_dir / "funding_api_reconciliation.json", reconciliations)
    summary["funding_api_reconciliation"] = reconciliations
    errors += [
        {"stage": "funding_api_reconciliation", **r}
        for r in reconciliations
        if r["status"] in ("unresolved_conflict", "unresolved")
    ]
    summary["http_cache_hits"] = sum(r["cache_hit"] for r in sources)
    summary["http_fetches_this_run"] = sum(not r["cache_hit"] for r in sources)
    summary.update(
        success=not errors and len(cap_rows) == 32 and not cap_missing,
        diagnostic_only=True,
        historical_eligible_universe_ready=False,
        errors=errors,
        sources=sources,
        tool_sha256=digest(Path(__file__).read_bytes()),
        lifecycle_ledger_sha256=digest((args.lifecycle_dir / "identity_ledger.json").read_bytes()),
        paper_and_live="deferred_until_after_OOS_review",
    )
    readiness = {
        "diagnostic_checks_passed": summary["success"],
        "historical_eligible_universe_ready": False,
        "normalized_observations": {
            "status": "build_passed",
            "partitions": release["verified_partitions"],
        },
        "size": {
            "status": "source_pilots_only",
            "historical_mappings_approved": 0,
            "CMC_snapshot_rows": len(snapshot_rows),
            "CoinMetrics_pilot_rows": len(cap_rows),
            "unresolved": [
                "full_requested_history_coverage",
                "episode_specific_asset_IDs",
                "source_definition_choice",
                "publication_latency_and_revisions",
            ],
        },
        "lifecycle": {
            "status": "partial_official_evidence",
            "priority_with_events": lifecycle_summary["priority_with_official_events"],
            "priority_identifiers": lifecycle_summary["priority_identifiers"],
            "official_sources": lifecycle_summary["official_sources"],
            "official_events": lifecycle_summary["verified_events"],
            "complete_lifecycles_verified": lifecycle_summary["full_lifecycle_verified"],
            "unresolved": [
                "selected_contract_episode_boundaries",
                "historical_specifications",
                "terminal_settlement_prices",
                "historical_announcement_versions",
            ],
        },
        "funding": {
            "status": "observations_reconciled_on_pilot_only",
            "cashflow_ready": False,
            "unresolved": [
                "historical_prediction_availability",
                "settlement_prices_on_uncovered_events",
                "position_snapshot_and_event_order",
                "inactive_or_reused_contract_observations",
            ],
        },
        "simulation_and_strategy_experiments_started": False,
        "paper_and_live": "deferred_until_after_OOS_review",
    }
    write_json(args.output_dir / "readiness.json", readiness)
    write_json(args.output_dir / "summary.json", summary)
    compact = {key: value for key, value in summary.items() if key != "sources"}
    compact["source_count"] = len(sources)
    print(json.dumps(compact, sort_keys=True))
    return summary["success"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release", type=Path, default=SHARED / "canonical/binance_um_research/v20261117_001"
    )
    parser.add_argument(
        "--lifecycle-dir",
        type=Path,
        default=ROOT / "data/interim/usdm_universe/lifecycle_review_20261118",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "data/interim/research_input_readiness/20261118"
    )
    args = parser.parse_args()
    with exclusive_run(args.output_dir / ".check.lock"):
        raise SystemExit(0 if run(args) else 1)
