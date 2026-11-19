"""Public2020 cap/identity coverage leads; no approved joins or strategy outcomes."""

from __future__ import annotations

import argparse
import bisect
import json
import statistics
import sys
import time
import traceback
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from build_early_research import FULL as EARLY
from check_research_inputs import parse_snapshot
from collect_cmc_weekly import (
    DEFAULT as OLD,
)
from collect_cmc_weekly import (
    CalendarLinks,
    Downloader,
    LogTee,
    checked_source,
    partition,
    raw_bytes,
    write_source,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/interim/early_size_inventory_20261119"
PILOT = ["20200105", "20200503", "20200830", "20201227"]
DAY = 86400000
PANEL_FIELDS = [
    "instrument_id",
    "data_day",
    "reference_time_ms",
    "valid_closing_observation",
    "complete_trade_day",
    "price_history_diagnostic_candidate",
    "funding_freshness_diagnostic",
    "known_composite_index",
    "audit_at_or_after_confirmed_settlement",
]


def dates():
    labels = ["20191222", "20191229"]
    cursor = date(2020, 1, 5)
    while cursor.year == 2020:
        labels.append(cursor.strftime("%Y%m%d"))
        cursor += timedelta(days=7)
    return labels


def decision_times():
    return [
        int((datetime(2020, 1, 6, tzinfo=UTC) + timedelta(days=7 * n)).timestamp() * 1000)
        for n in range(52)
    ]


def available(label):
    return int(
        (datetime.strptime(label, "%Y%m%d").replace(tzinfo=UTC) + timedelta(days=8)).timestamp()
        * 1000
    )


def snapshot_at(reference, labels):
    ordered = sorted((available(label), label) for label in labels)
    index = bisect.bisect_right([value for value, _ in ordered], reference) - 1
    if index < 0 or reference >= ordered[index][0] + 7 * DAY:
        return None
    return ordered[index][1]


def literal_match(instrument, rows, is_index=False):
    if is_index:
        return "excluded_composite_index", []
    stem = instrument.removesuffix("USDT").casefold()
    candidates = [row for row in rows if row["symbol"].casefold() == stem]
    ids = {row["vendor_asset_id"] for row in candidates}
    if len(ids) != len(candidates):
        raise ValueError("duplicate same-date vendor ID")
    return "missing_literal" if not ids else "ambiguous_same_date" if len(
        ids
    ) > 1 else "literal_unverified", candidates


def load_panel():
    manifest_body = (EARLY / "manifest.json").read_bytes()
    manifest = json.loads(manifest_body)
    if (
        not manifest["success"]
        or not manifest["full_scope"]
        or manifest["identifiers"] != 81
        or manifest["daily_rows"] != 29646
        or manifest["historical_size_integrated"]
    ):
        raise ValueError("require completed unmodified early observation panel")
    requested = set(decision_times())
    panel, index_hashes, daily_hashes = {}, {}, {}
    paths = sorted((EARLY / "index").glob("*.json"))
    if len(paths) != 81:
        raise ValueError("early identifier count changed")
    for path in paths:
        body = path.read_bytes()
        index = json.loads(body)
        symbol = index["instrument_id"]
        if path.stem != symbol or index["daily_path"] != f"daily/{symbol}.parquet":
            raise ValueError("early index identity/path mismatch")
        data = (EARLY / index["daily_path"]).read_bytes()
        if digest(data) != index["daily_sha256"]:
            raise ValueError("early daily panel integrity failure")
        table = pq.read_table(pa.BufferReader(data), columns=PANEL_FIELDS, use_threads=False)
        if table.num_rows != 366:
            raise ValueError("early daily calendar changed")
        selected = [r for r in table.to_pylist() if r["reference_time_ms"] in requested]
        if len(selected) != 52 or len({r["reference_time_ms"] for r in selected}) != 52:
            raise ValueError("weekly panel rows missing or duplicated")
        if any(r["instrument_id"] != symbol for r in selected):
            raise ValueError("daily row identity mismatch")
        panel[symbol] = {r["reference_time_ms"]: r for r in selected}
        index_hashes[symbol], daily_hashes[symbol] = digest(body), digest(data)
    return panel, {
        "early_manifest_sha256": digest(manifest_body),
        "early_index_hashes": index_hashes,
        "early_daily_hashes": daily_hashes,
    }


def summarize(panel, captured, requested):
    weekly, per_asset = (
        [],
        {
            symbol: {
                "instrument_id": symbol,
                "active_weeks": 0,
                "price_history_candidate_weeks": 0,
                "price_history_literal_size_lead_weeks": 0,
                "missing_size_in_price_history_weeks": [],
                "ambiguous_size_in_price_history_weeks": [],
            }
            for symbol in sorted(panel)
        },
    )
    for reference in decision_times():
        required = snapshot_at(reference, requested)
        observed = required in captured
        item = {
            "decision_date": datetime.fromtimestamp(reference / 1000, UTC).date().isoformat(),
            "required_snapshot_date": required,
            "snapshot_captured": observed,
            "active_single_token_diagnostic": 0,
            "price_history_candidates": 0,
            "literal_size_active_leads": 0,
            "literal_size_price_history_leads": 0,
            "literal_size_price_and_fresh_funding_leads": 0,
        }
        for symbol, records in panel.items():
            row = records[reference]
            active = (
                row["valid_closing_observation"]
                and row["complete_trade_day"]
                and not row["known_composite_index"]
                and not row["audit_at_or_after_confirmed_settlement"]
            )
            price = row["price_history_diagnostic_candidate"]
            status, _ = literal_match(
                symbol, captured.get(required, []), row["known_composite_index"]
            )
            has_size = observed and status == "literal_unverified"
            item["active_single_token_diagnostic"] += int(active)
            item["price_history_candidates"] += int(price)
            item["literal_size_active_leads"] += int(active and has_size)
            item["literal_size_price_history_leads"] += int(price and has_size)
            item["literal_size_price_and_fresh_funding_leads"] += int(
                price and has_size and row["funding_freshness_diagnostic"]
            )
            asset = per_asset[symbol]
            asset["active_weeks"] += int(active)
            asset["price_history_candidate_weeks"] += int(price)
            asset["price_history_literal_size_lead_weeks"] += int(price and has_size)
            if price and observed and not has_size:
                asset[
                    "ambiguous_size_in_price_history_weeks"
                    if status == "ambiguous_same_date"
                    else "missing_size_in_price_history_weeks"
                ].append(item["decision_date"])
        weekly.append(item)
    for symbol, asset in per_asset.items():
        found, missing, ambiguous, names = defaultdict(list), [], [], defaultdict(list)
        for label, rows in sorted(captured.items()):
            is_index = any(r["known_composite_index"] for r in panel[symbol].values())
            status, candidates = literal_match(symbol, rows, is_index)
            if status == "missing_literal":
                missing.append(label)
            if status == "ambiguous_same_date":
                ambiguous.append(label)
            for row in candidates:
                found[row["vendor_asset_id"]].append(
                    {"date": label, "name": row["name"], "symbol": row["symbol"]}
                )
            if not candidates and not is_index:
                for row in rows:
                    if row["name"].casefold() == symbol.removesuffix("USDT").casefold():
                        names[row["vendor_asset_id"]].append(
                            {"date": label, "name": row["name"], "symbol": row["symbol"]}
                        )
        asset.update(
            literal_vendor_proposals={str(k): v for k, v in found.items()},
            literal_IDs_change_or_multiple=len(found) > 1,
            missing_literal_snapshot_dates=missing,
            ambiguous_same_date_snapshot_dates=ambiguous,
            name_only_proposals_not_joins={str(k): v for k, v in names.items()},
            approved_historical_mapping=None,
        )
    return weekly, list(per_asset.values())


def seed_source(label):
    url = "https://coinmarketcap.com/historical/" + ("" if label == "calendar" else label + "/")
    if checked_source(OUTPUT, label, url) is None:
        previous = checked_source(OLD, label, url)
        if previous:
            write_source(OUTPUT, label, previous[0], previous[1])
    return url


def run(args):
    if args.action == "summary":
        for folder in ("pilot", "full"):
            path = OUTPUT / folder / "summary.json"
            print(
                json.dumps({"path": str(path), **read_json(path)})
                if path.exists()
                else f"{path}: not run"
            )
        return
    started = time.monotonic()
    if args.max_mib != 64:
        raise ValueError("registered raw budget is64MiB")
    with exclusive_run(OUTPUT / ".inventory.lock"):
        if (OUTPUT / "access_pause.json").exists():
            raise ValueError(
                "source access stopped;inspect access_pause.json without automatic retry"
            )
        if raw_bytes(OUTPUT) > 64 * 1024**2:
            raise ValueError("raw budget exceeded")
        calendar_url = seed_source("calendar")
        calendar, calendar_meta, _ = checked_source(OUTPUT, "calendar", calendar_url)
        links = CalendarLinks()
        links.feed(calendar.decode("utf-8"))
        requested = dates()
        if len(requested) != 54 or set(requested) - links.dates:
            raise ValueError("registered54-date calendar incomplete")
        plan = {
            "dates": requested,
            "carry_in_dates": requested[:2],
            "calendar_sha256": calendar_meta["sha256"],
            "source_scope": "first public page only,not all assets",
            "lag_days": 7,
            "valid_days": 7,
        }
        bind_run(OUTPUT / "calendar_contract", plan)
        panel, early_binding = load_panel()
        selected = PILOT if args.action == "pilot" else requested
        target = OUTPUT / args.action
        binding = {
            **early_binding,
            "plan": plan,
            "selected_dates": selected,
            "script_sha256": digest(Path(__file__).read_bytes()),
            "dependencies": {
                name: digest((ROOT / "scripts" / name).read_bytes())
                for name in (
                    "collect_cmc_weekly.py",
                    "check_research_inputs.py",
                    "acquire_usdm_universe.py",
                )
            },
        }
        bind_run(target, binding)
        downloader = Downloader(OUTPUT, 64 * 1024**2)
        captured, reused = {}, 0
        for number, label in enumerate(selected, 1):
            url = seed_source(label)
            if checked_source(OUTPUT, label, url) is None:
                for path in (OUTPUT / "raw/attempts" / label).glob("*.json"):
                    meta = read_json(path)
                    body = path.with_suffix(".raw").read_bytes()
                    if digest(body) != meta["sha256"]:
                        raise ValueError("failed source evidence corrupted")
                    if (
                        meta.get("attempt") == 3 and (not meta["status"] or meta["status"] >= 500)
                    ) or meta["status"] in (202, 404):
                        raise ValueError("terminal source failure frozen for this review")
            rows, report, cached = partition(OUTPUT, target, label, downloader)
            body, provenance, _ = checked_source(OUTPUT, label, url)
            fresh = parse_snapshot(body, label)
            for row in fresh:
                row["source"] = provenance
            if rows != fresh or report["rows"] != len(rows):
                raise ValueError("fresh metadata parse/partition mismatch")
            captured[label] = rows
            reused += int(cached)
            if number % 10 == 0 or number == len(selected):
                print(
                    f"early Size snapshots {number}/{len(selected)}; HTTP={downloader.requests}",
                    flush=True,
                )
        weekly, assets = summarize(panel, captured, requested)
        full = args.action == "full"
        if full and (len(captured) != 54 or not all(r["snapshot_captured"] for r in weekly)):
            raise ValueError("full weekly source coverage incomplete")
        write_json(target / "weekly_coverage.json", weekly)
        write_json(target / "asset_review_queue.json", assets)
        complete_weeks = [r for r in weekly if r["snapshot_captured"]]
        price_total = sum(r["price_history_candidates"] for r in complete_weeks)
        lead_total = sum(r["literal_size_price_history_leads"] for r in complete_weeks)
        result = {
            "success": True,
            "errors": [],
            "full_scope": full,
            "captured_snapshot_dates": len(captured),
            "snapshot_rows": sum(map(len, captured.values())),
            "identifiers_reviewed": len(assets),
            "weekly_decisions": len(weekly),
            "weekly_decisions_with_captured_source": len(complete_weeks),
            "unique_vendor_ids": len(
                {r["vendor_asset_id"] for rows in captured.values() for r in rows}
            ),
            "literal_proposal_identifiers": sum(
                bool(r["literal_vendor_proposals"]) for r in assets
            ),
            "name_only_proposal_identifiers": sum(
                bool(r["name_only_proposals_not_joins"]) for r in assets
            ),
            "price_candidate_asset_weeks": price_total,
            "literal_size_price_lead_asset_weeks": lead_total,
            "conditional_literal_size_price_lead_fraction": lead_total / price_total
            if price_total
            else None,
            "weekly_literal_size_price_leads": {
                "minimum": min(r["literal_size_price_history_leads"] for r in complete_weeks),
                "median": statistics.median(
                    r["literal_size_price_history_leads"] for r in complete_weeks
                ),
                "maximum": max(r["literal_size_price_history_leads"] for r in complete_weeks),
            },
            "source_http_requests_this_run": downloader.requests,
            "verified_raw_cache_hits": reused,
            "raw_evidence_bytes": raw_bytes(OUTPUT),
            "approved_historical_mappings": 0,
            "historical_Size_publication_vintage_proven": False,
            "all_asset_coverage_proven": False,
            "historical_eligible_universe_ready": False,
            "OOS_performance_inspected": False,
            "factor_values_computed": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        write_json(target / "summary.json", result)
        print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pilot", "full", "summary"))
    parser.add_argument("--max-mib", type=int, default=64)
    args = parser.parse_args()
    log = ROOT / "reports/acquisition" / f"early_size_{args.action}_20261119.log"
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
