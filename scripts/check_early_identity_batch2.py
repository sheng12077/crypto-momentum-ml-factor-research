"""Corroborate a fixed early identity batch without materializing research joins."""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

import check_early_identity_batch as previous_batch
import inventory_early_size as inventory
import verify_early_size_identities as identity
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from check_early_identity_batch import historical_check, rule, source_terms
from collect_cmc_weekly import Downloader, LogTee, checked_source, raw_bytes

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/early_identity_batch2_20261119.json"
OUTPUT = ROOT / "data/interim/early_identity_batch2_20261119"


def select_priority(ranked, previous_rules, prior_cases):
    # A reviewed-but-pending case must not consume the next batch's source budget.
    excluded = {row["instrument_id"] for row in previous_rules} | set(prior_cases)
    return [row for row in ranked if row["instrument_id"] not in excluded][:8]


def provider_labels_match(asset, current):
    if current["id"] != asset["vendor_asset_id"]:
        return False
    names = {name.casefold() for name in asset.get("provider_names", [asset["name"]])}
    return current["symbol"] == asset["symbol"] and current["name"].casefold() in names


def sources(config):
    result = []
    if config["expected_sources"] != 24:
        raise ValueError("registered source budget changed")
    for spec in config["sources"]:
        spec = dict(spec)
        if "article_code" in spec:
            spec["url"] = (
                "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode="
                + spec["article_code"]
            )
        result.append(spec)
    if len(result) != 24 or len({s["id"] for s in result}) != 24:
        raise ValueError("fixed source count changed")
    return result


def capture(config, specs):
    target = OUTPUT / "capture_summary.json"
    if target.exists():
        report = read_json(target)
        if report["config_sha256"] != digest(CONFIG.read_bytes()):
            raise ValueError("capture configuration changed")
        for path in (OUTPUT / "raw/attempts").rglob("*.json"):
            meta = read_json(path)
            body = path.with_suffix(".raw").read_bytes()
            if digest(body) != meta["sha256"] or len(body) != meta["bytes"]:
                raise ValueError("failed response integrity mismatch")
        return report, 0
    if (OUTPUT / "access_pause.json").exists():
        raise ValueError("capture stopped; no automatic retry")
    downloader = Downloader(OUTPUT, config["max_raw_bytes"])
    results, failures = [], []
    for spec in specs:
        try:
            _, meta, cached = downloader.get(spec["id"], spec["url"])
            results.append({"id": spec["id"], "source": meta, "cache_hit": cached})
        except Exception as exc:
            failures.append({"id": spec["id"], "error": str(exc)})
            if (OUTPUT / "access_pause.json").exists():
                break
    report = {
        "success": len(results) == len(specs),
        "config_sha256": digest(CONFIG.read_bytes()),
        "results": results,
        "failures": failures,
        "http_requests": downloader.requests,
        "raw_bytes": raw_bytes(OUTPUT),
    }
    write_json(target, report)
    return report, downloader.requests


def run(review_name):
    config = read_json(CONFIG)
    specs = sources(config)
    dependencies = (
        "check_early_identity_batch.py",
        "acquire_usdm_universe.py",
        "collect_cmc_weekly.py",
        "inventory_early_size.py",
        "verify_early_size_identities.py",
        "followup_early_identities.py",
        "check_early_cases.py",
        "review_contract_identity.py",
        "check_identity_followup.py",
    )
    with exclusive_run(OUTPUT / ".batch.lock"):
        bind_run(OUTPUT / "capture_contract", {"config_sha256": digest(CONFIG.read_bytes())})
        previous_root = ROOT / config["previous_review"]
        if not (previous_root.parent / "capture_summary.json").exists():
            raise ValueError("previous frozen capture missing; do not reacquire")
        if previous_root != previous_batch.OUTPUT / "review_002":
            raise ValueError("unexpected prior review")
        previous_batch.run("review_002")
        previous_rules = read_json(previous_root / "mapping_decisions.json")
        previous_queue = read_json(previous_root / "asset_review_queue.json")
        _, historical_hashes = identity.historical_ids()
        captured_history = {
            label: read_json(inventory.OUTPUT / "full/partitions" / (label + ".json"))
            for label in inventory.dates()
        }
        historical = [row for rows in captured_history.values() for row in rows]
        panel, early_hashes = inventory.load_panel()
        _, queue = inventory.summarize(panel, captured_history, inventory.dates())
        original_queue = read_json(inventory.OUTPUT / "full/asset_review_queue.json")
        if queue != original_queue:
            raise ValueError("recomputed inventory queue differs")
        ranked = sorted(
            queue, key=lambda a: (-a["price_history_candidate_weeks"], a["instrument_id"])
        )
        selected = select_priority(ranked, previous_rules, config["prior_cases"])
        if [a["instrument_id"] for a in selected] != [a["instrument_id"] for a in config["assets"]]:
            raise ValueError("preregistered priority selection changed")
        capture_report, requests = capture(config, specs)
        captured = {}
        for spec in specs:
            found = checked_source(OUTPUT, spec["id"], spec["url"])
            if found is not None:
                captured[spec["id"]] = found
        specification = {s["id"]: s for s in specs}
        reports, rules, providers = {}, [], {}
        for asset in config["assets"]:
            symbol = asset["instrument_id"]
            history_ok, history_report = historical_check(asset, historical)
            proof = {
                "historical_identity": history_ok,
                "provider_identity": False,
                "venue_name": False,
                "venue_futures": False,
                "token_contract": True,
            }
            reports[symbol] = {"history": history_report}
            if asset["provider"] in captured:
                try:
                    current = identity.provider(
                        captured[asset["provider"]][0], asset["vendor_asset_id"]
                    )
                    providers[symbol] = current
                    proof["provider_identity"] = provider_labels_match(asset, current)
                except (ValueError, KeyError, TypeError) as exc:
                    reports[symbol]["provider_error"] = str(exc)
            for gate, label, terms in (
                ("venue_name", asset["name_source"], asset["name_terms"]),
                ("venue_futures", asset["future_source"], asset["future_terms"]),
            ):
                proof[gate], reports[symbol][gate] = source_terms(
                    label, terms, captured, specification
                )
            if "ethereum_contract" in asset:
                expected = asset["ethereum_contract"]
                origin_ok, reports[symbol]["contract_origin"] = source_terms(
                    "link_contract", [expected], captured, specification
                )
                proof["token_contract"] = (
                    symbol in providers
                    and identity.ethereum_contract(providers[symbol], expected)
                    and origin_ok
                )
            decision = rule(asset, proof, config["scope_end_exclusive"])
            start = datetime.fromisoformat(decision["scope_from"]).timestamp() * 1000
            end = datetime.fromisoformat(decision["scope_to_exclusive"]).timestamp() * 1000
            decision["price_history_candidate_weeks_in_scope"] = sum(
                start <= stamp < end and row["price_history_diagnostic_candidate"]
                for stamp, row in panel[symbol].items()
            )
            rules.append(decision)
        previous_by_id = {item["instrument_id"]: item for item in previous_queue}
        for item in ranked:
            item["batch1_status"] = previous_by_id[item["instrument_id"]]["batch1_status"]
            found = next((r for r in rules if r["instrument_id"] == item["instrument_id"]), None)
            item["batch2_status"] = (
                "corroborated_identity"
                if found and found["size_identity_join_allowed"]
                else "pending_batch2"
                if found
                else "outside_batch2"
            )
            item["strict_strategy_eligible"] = False
        binding = {
            "previous_review_hashes": {
                p.name: digest(p.read_bytes()) for p in previous_root.glob("*.json")
            },
            "config_sha256": digest(CONFIG.read_bytes()),
            "script_sha256": digest(Path(__file__).read_bytes()),
            "dependencies": {
                name: digest((ROOT / "scripts" / name).read_bytes()) for name in dependencies
            },
            "historical_hashes": historical_hashes,
            **early_hashes,
            "capture_summary_sha256": digest((OUTPUT / "capture_summary.json").read_bytes()),
            "captured_sources": {k: v[1]["sha256"] for k, v in captured.items()},
        }
        target = OUTPUT / review_name
        bind_run(target, binding)
        write_json(target / "mapping_decisions.json", rules)
        write_json(target / "evidence_checks.json", reports)
        write_json(target / "provider_identities.json", providers)
        write_json(target / "asset_review_queue.json", ranked)
        result = {
            "review_completed": True,
            "source_capture_complete": capture_report["success"],
            "source_http_requests_this_run": requests,
            "captured_sources": len(captured),
            "reviewed_identifiers": len(rules),
            "retained_queue_identifiers": len(ranked),
            "reviewed_price_candidate_asset_weeks": sum(
                a["price_history_candidate_weeks"] for a in selected
            ),
            "corroborated_identity_rules": [
                r["instrument_id"] for r in rules if r["size_identity_join_allowed"]
            ],
            "pending_identity_rules": [
                r["instrument_id"] for r in rules if not r["size_identity_join_allowed"]
            ],
            "corroborated_in_scope_price_candidate_asset_weeks": sum(
                r["price_history_candidate_weeks_in_scope"]
                for r in rules
                if r["size_identity_join_allowed"]
            ),
            "previous_pending_identity_rules": [
                r["instrument_id"] for r in previous_rules if not r["size_identity_join_allowed"]
            ],
            "historical_eligible_universe_ready": False,
            "historical_Size_publication_vintage_proven": False,
            "canonical_joins_materialized": 0,
            "OOS_performance_inspected": False,
        }
        write_json(target / "summary.json", result)
        print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "summary"))
    parser.add_argument("--review", default="review_001", choices=("review_001", "review_002"))
    args = parser.parse_args()
    if args.action == "summary":
        print(json.dumps(read_json(OUTPUT / args.review / "summary.json"), sort_keys=True))
        return
    path = ROOT / "reports/acquisition/early_identity_batch2_20261119.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    print("Log: " + str(path), flush=True)
    with (
        path.open("a", encoding="utf-8") as handle,
        redirect_stdout(LogTee(sys.stdout, handle)),
        redirect_stderr(LogTee(sys.stderr, handle)),
    ):
        run(args.review)


if __name__ == "__main__":
    main()
