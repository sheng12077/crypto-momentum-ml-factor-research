"""Retention-first metadata screening; outputs are candidates, not a trading pool."""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from collect_cmc_weekly import LogTee

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/interim"
UNIVERSE = DATA / "usdm_universe"
PILOT = ["BTCUSDT", "ETHUSDT", "BNXUSDT", "SUNUSDT", "1MBABYDOGEUSDT"]
DEFAULT = DATA / "full_universe_screen_20261118"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_inputs():
    paths = {
        "plan": UNIVERSE / "census_full_20261117/download_plan.json",
        "quality": UNIVERSE / "audit_20261117/symbol_quality.json",
        "audit": UNIVERSE / "audit_20261117/summary.json",
        "download": UNIVERSE / "download_full_20261117/summary.json",
        "bounds": UNIVERSE / "audit_20261117/series_observed_bounds.json",
        "ledger": UNIVERSE / "lifecycle_review_20261118/identity_ledger.json",
        "lifecycle_summary": UNIVERSE / "lifecycle_review_20261118/summary.json",
        "cmc_queue": DATA / "cmc_identity_audit_002_20261118/identity_review_queue.json",
        "vendors": DATA / "cmc_identity_audit_002_20261118/vendor_identity_history.json",
        "prior_review": DATA / "contract_identity_review_20261118/review_002/summary.json",
        "episode_facts": ROOT / "config/contract_identity_evidence_20261118.json",
        "policy": ROOT / "config/identity_decisions_20261118.json",
        "policy_binding": DATA / "identity_followup_20261118/decisions/run_config.json",
        "release": ROOT.parents[1]
        / "data/canonical/binance_um_research/v20261117_001/manifest.json",
    }
    bodies = {key: path.read_bytes() for key, path in paths.items()}
    hashes = {key: digest(body) for key, body in bodies.items()}
    data = {key: json.loads(body) for key, body in bodies.items()}
    plan = data["plan"]
    require(plan["complete_census"] and plan["window"] == ["2021-01", "2026-10"], "plan scope")
    count = len(plan["files"])
    require(
        data["download"]["success"]
        and not data["download"]["errors"]
        and data["download"]["requested_selection_complete"],
        "download incomplete",
    )
    require(
        data["download"]["verified_files"]
        == count
        == data["audit"]["verified_raw_files"]
        == data["release"]["verified_partitions"],
        "file counts mismatch",
    )
    require(
        data["audit"]["success"] and data["audit"]["integrity_error_count"] == 0, "audit failed"
    )
    require(
        data["release"]["success"]
        and data["release"]["full_scope"]
        and data["release"]["inputs"]["plan_sha256"] == hashes["plan"],
        "release/plan mismatch",
    )
    require(
        data["lifecycle_summary"]["success"]
        and data["lifecycle_summary"]["ledger_sha256"] == hashes["ledger"],
        "ledger integrity",
    )
    prior = data["prior_review"]
    require(
        prior["success"]
        and prior["inputs"]["queue_sha256"] == hashes["cmc_queue"]
        and prior["inputs"]["vendor_history_sha256"] == hashes["vendors"],
        "CMC review integrity",
    )
    require(
        prior["inputs"]["config_sha256"] == hashes["episode_facts"]
        and data["policy_binding"]["policy_sha256"] == hashes["policy"],
        "curated policy integrity",
    )
    population = {r["instrument_id"] for r in data["ledger"]}
    require(len(population) == data["audit"]["symbol_count"], "population count")
    require({r["symbol"] for r in plan["files"]} <= population, "unplanned file identifier")
    for key, field in (
        ("ledger", "instrument_id"),
        ("quality", "symbol"),
        ("cmc_queue", "instrument_id"),
    ):
        require(
            len(data[key]) == len(population) and {r[field] for r in data[key]} == population,
            "population mismatch: " + key,
        )
    require(
        set(data["bounds"]) == {r["symbol"] for r in plan["files"]},
        "observed bounds/file population",
    )
    require(len({r["key"] for r in plan["files"]}) == count, "duplicate plan key")
    for symbol in population:
        require(not any(t in symbol for t in ("/", "\\", "..")), "unsafe identifier")
    data["hashes"] = hashes
    return data


def prepare(data):
    ledger = {r["instrument_id"]: r for r in data["ledger"]}
    quality = {r["symbol"]: r for r in data["quality"]}
    queue = {r["instrument_id"]: r for r in data["cmc_queue"]}
    history = {r["vendor_asset_id"]: r for r in data["vendors"]}
    manual = {r["instrument_id"]: r for r in data["episode_facts"]["records"]}
    updates = {
        r["instrument_id"]: r["proposed_vendor_asset_id"] for r in data["policy"]["vendor_updates"]
    }
    updates["1000SATSUSDT"] = data["policy"]["sats"]["primary_historical_vendor_asset_id"]
    whole = {
        r["instrument_id"]
        for r in data["policy"]["whole_identifier_exclusions"]
        if "size_join" in r["scopes"]
    }
    calendar = defaultdict(lambda: defaultdict(set))
    trades = defaultdict(list)
    for item in data["plan"]["files"]:
        calendar[item["symbol"]][item["kind"]].add(item["month"])
        if item["kind"] == "trade":
            trades[item["symbol"]].append(item)
    records = []
    for symbol, identity in sorted(ledger.items()):
        q = queue[symbol]
        ids = {r["vendor_asset_id"] for r in q["candidates_for_manual_review_only"]}
        basis = "literal_symbol_review_lead_only"
        if symbol in manual:
            ids = {
                e["proposed_vendor_asset_id"]
                for e in manual[symbol]["proposed_episodes"]
                if e["proposed_vendor_asset_id"] is not None
            }
            basis = "curated_partial_episode_proposals"
        if symbol in updates:
            ids, basis = {updates[symbol]}, "explicit_reviewed_override"
        rejected = {
            r["vendor_asset_id"]
            for r in data["policy"]["rejected_vendor_associations"]
            if r["instrument_id"] == symbol
        }
        ids -= rejected
        captured = sorted(v for v in ids if v in history)
        overlap = sorted(
            set.intersection(
                *(calendar[symbol].get(kind, set()) for kind in ("trade", "mark", "funding"))
            )
        )
        has_activity = quality[symbol]["first_positive_trade_bar"] is not None
        records.append(
            {
                "instrument_id": symbol,
                "positive_trade_observed": has_activity,
                "raw_data_disposition": "retain_for_further_checks"
                if has_activity
                else "withhold_no_positive_trade_observed",
                "three_series_months": overlap,
                "three_series_overlap": bool(overlap),
                "proposed_vendor_IDs": sorted(ids),
                "captured_vendor_IDs": captured,
                "mapping_basis": basis,
                "Size_join_whole_identifier_blocked": symbol in whole,
                "Size_history_lead_after_component_gate": bool(captured) and symbol not in whole,
                "current_noncoin_annotation_only": identity["current_noncoin_annotation"],
                "current_metadata_missing": identity.get("current_product_metadata") is None,
                "review_flags": quality[symbol]["review_flags"],
                "stub_trade_months": quality[symbol]["constant_zero_volume_trade_months"],
                "known_identity_reuse": identity["known_identity_reuse"],
                "scoped_restrictions": [
                    r for r in data["policy"]["interval_exclusions"] if r["instrument_id"] == symbol
                ],
                "historical_strategy_eligible": False,
                "automatic_join_approved": False,
            }
        )
    return records, calendar, trades, history


def quick_summary(records):
    return {
        "success": True,
        "errors": [],
        "identifiers": len(records),
        "positive_trade_observed": sum(r["positive_trade_observed"] for r in records),
        "no_positive_trade_identifiers": [
            r["instrument_id"] for r in records if not r["positive_trade_observed"]
        ],
        "three_series_overlap": sum(r["three_series_overlap"] for r in records),
        "Size_vendor_ID_proposals": sum(bool(r["proposed_vendor_IDs"]) for r in records),
        "Size_captured_history_leads_after_component_gate": sum(
            r["Size_history_lead_after_component_gate"] for r in records
        ),
        "Size_leads_with_current_noncoin_annotation_need_class_review": sum(
            r["Size_history_lead_after_component_gate"] and r["current_noncoin_annotation_only"]
            for r in records
        ),
        "Size_leads_missing_current_metadata_retained_for_review": sum(
            r["Size_history_lead_after_component_gate"] and r["current_metadata_missing"]
            for r in records
        ),
        "current_noncoin_annotations_not_exclusions": sum(
            r["current_noncoin_annotation_only"] for r in records
        ),
        "missing_current_metadata_not_exclusions": sum(
            r["current_metadata_missing"] for r in records
        ),
        "identifiers_with_stub_months_retained_elsewhere": sum(
            bool(r["stub_trade_months"]) and r["positive_trade_observed"] for r in records
        ),
        "candidate_counts_are_not_crypto_or_tradability_certification": True,
        "historical_eligible_universe_ready": False,
        "historical_joins_approved": 0,
        "OOS_performance_inspected": False,
    }


def trade_report(item, reports_dir):
    path = reports_dir / (digest(item["key"].encode()) + ".json")
    body = path.read_bytes()
    report = json.loads(body)
    require(
        all(report[k] == item[k] for k in ("key", "symbol", "kind", "month")),
        "report identity mismatch",
    )
    require(report["bytes"] == item["size"], "report bytes mismatch")
    quality = report["quality"]
    total, positive, zero = (
        quality[k] for k in ("row_count", "positive_volume_rows", "zero_volume_rows")
    )
    require(
        all(type(v) is int and v >= 0 for v in (total, positive, zero))
        and total == positive + zero,
        "report activity counts",
    )
    first, last = quality["first_positive_volume_time"], quality["last_positive_volume_time"]
    require(
        (positive > 0) == (first is not None and last is not None),
        "activity timestamps/count mismatch",
    )
    if positive:
        require(
            datetime.fromisoformat(first) <= datetime.fromisoformat(last), "activity time ordering"
        )
    return {
        "month": item["month"],
        "rows": total,
        "positive_rows": positive,
        "zero_rows": zero,
        "first_positive": first,
        "last_positive": last,
        "constant_stub": quality["zero_volume_constant_trade_artifact"],
        "report_sha256": digest(body),
        "raw_sha256_from_prior_audit": report["sha256"],
    }


def scan_symbol(record, items, calendar, history, output, reports_dir, first_positive):
    symbol = record["instrument_id"]
    months = [trade_report(item, reports_dir) for item in sorted(items, key=lambda r: r["month"])]
    checkpoint = output / "checkpoints" / (symbol + ".json")
    index = output / "indexes" / (symbol + ".json")
    report_hashes = {m["month"]: m["report_sha256"] for m in months}
    if index.exists():
        previous = read_json(index)
        require(
            previous["checkpoint_sha256"] == digest(checkpoint.read_bytes()), "checkpoint corrupted"
        )
        require(
            previous["report_hashes"] == report_hashes,
            "acquisition reports changed since checkpoint",
        )
        return read_json(checkpoint), True
    require(not checkpoint.exists(), "unmanifested checkpoint; inspect before retry")
    size_months = {
        a["date"][:4] + "-" + a["date"][4:6]
        for vendor in record["captured_vendor_IDs"]
        for a in history[vendor]["appearances"]
    }
    first = datetime.fromisoformat(first_positive) if first_positive else None
    for month in months:
        active = month["positive_rows"] > 0
        month["three_series_present_with_active_trade"] = (
            active and month["month"] in record["three_series_months"]
        )
        month["potential_Size_overlap_somewhere_in_month"] = (
            active
            and month["month"] in size_months
            and not record["Size_join_whole_identifier_blocked"]
        )
        month["elapsed_120_day_history_possible_not_valid_closes"] = bool(
            active
            and first
            and (datetime.fromisoformat(month["last_positive"]) - first).total_seconds()
            >= 120 * 86400
        )
        month["scoped_restrictions_require_row_level_application"] = bool(
            record["scoped_restrictions"]
        )
    result = {
        "instrument_id": symbol,
        "months": months,
        "historical_strategy_eligible": False,
        "interpretation": "month activity/calendar diagnostic; Size overlaps are coarse, availability and episode timing unproven",
    }
    write_json(checkpoint, result)
    write_json(
        index,
        {"report_hashes": report_hashes, "checkpoint_sha256": digest(checkpoint.read_bytes())},
    )
    return result, False


def run(args):
    data = load_inputs()
    records, calendar, trades, history = prepare(data)
    inputs = {**data["hashes"], "tool_sha256": digest(Path(__file__).read_bytes())}
    if args.action == "summary":
        for mode in ("quick", "pilot", "full"):
            path = args.output / mode / "summary.json"
            print(
                json.dumps({"path": str(path), **read_json(path)}, sort_keys=True)
                if path.exists()
                else str(path) + ": not run"
            )
        return
    output = args.output / args.action
    selected = PILOT if args.action == "pilot" else [r["instrument_id"] for r in records]
    bind_run(output, {"inputs": inputs, "selected_symbols": selected})
    if args.action == "quick":
        write_json(output / "review_queue.json", records)
        summary = quick_summary(records)
    else:
        chosen = [r for r in records if r["instrument_id"] in selected]
        require(len(chosen) == len(selected), "selection mismatch")
        qualities = {r["symbol"]: r for r in data["quality"]}
        started, results, hits = time.monotonic(), [], 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = [
                pool.submit(
                    scan_symbol,
                    r,
                    trades.get(r["instrument_id"], []),
                    calendar,
                    history,
                    output,
                    UNIVERSE / "download_full_20261117/files",
                    qualities[r["instrument_id"]]["first_positive_trade_bar"],
                )
                for r in chosen
            ]
            try:
                for number, job in enumerate(as_completed(jobs), 1):
                    result, cached = job.result()
                    results.append(result)
                    hits += int(cached)
                    if number % 50 == 0 or number == len(jobs):
                        print(
                            f"screened {number}/{len(jobs)} identifiers; cached={hits}", flush=True
                        )
            except BaseException:
                for job in jobs:
                    job.cancel()
                raise
        results.sort(key=lambda r: r["instrument_id"])
        yearly = defaultdict(Counter)
        for row in results:
            for month in row["months"]:
                year = month["month"][:4]
                for key in (
                    "three_series_present_with_active_trade",
                    "potential_Size_overlap_somewhere_in_month",
                    "elapsed_120_day_history_possible_not_valid_closes",
                ):
                    yearly[year][key] += int(month[key])
                yearly[year]["trade_files"] += 1
        write_json(output / "yearly_instrument_month_counts.json", dict(sorted(yearly.items())))
        summary = {
            "success": True,
            "errors": [],
            "full_scope": args.action == "full",
            "identifiers": len(results),
            "trade_reports_verified": sum(len(r["months"]) for r in results),
            "expected_trade_reports": sum(len(trades.get(s, [])) for s in selected),
            "identifiers_with_active_trade_months": sum(
                any(m["positive_rows"] > 0 for m in r["months"]) for r in results
            ),
            "identifiers_with_three_series_active_months": sum(
                any(m["three_series_present_with_active_trade"] for m in r["months"])
                for r in results
            ),
            "identifiers_with_potential_Size_month_overlap": sum(
                any(m["potential_Size_overlap_somewhere_in_month"] for m in r["months"])
                for r in results
            ),
            "identifiers_with_possible_120_day_span": sum(
                any(m["elapsed_120_day_history_possible_not_valid_closes"] for m in r["months"])
                for r in results
            ),
            "cache_hits": hits,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "historical_eligible_universe_ready": False,
            "historical_joins_approved": 0,
            "OOS_performance_inspected": False,
        }
        require(
            summary["trade_reports_verified"] == summary["expected_trade_reports"],
            "trade report coverage incomplete",
        )
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["quick", "pilot", "full", "summary"])
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    require(1 <= args.workers <= 8, "workers must be1..8")
    log = ROOT / "reports/acquisition" / f"full_universe_screen_{args.action}_20261118.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    print("Log: " + str(log), flush=True)
    with (
        log.open("a", encoding="utf-8") as handle,
        redirect_stdout(LogTee(sys.stdout, handle)),
        redirect_stderr(LogTee(sys.stderr, handle)),
        exclusive_run(args.output / ".screen.lock"),
    ):
        try:
            run(args)
        except Exception:
            traceback.print_exc()
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
