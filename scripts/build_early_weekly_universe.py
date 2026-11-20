"""Consume BTC evidence in a new identity release and audit 2020 weekly coverage."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import statistics
import sys
import time
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path

import check_btc_public_api as btc_api
import inventory_early_size as inventory
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from collect_cmc_weekly import LogTee, checked_source
from run_early_identity import fingerprint, register_rule, repo_path, verify_output_hashes

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/early_weekly_universe_20261120.json"


def verify_tool(binding, name):
    if digest((ROOT / "scripts" / name).read_bytes()) != binding["script_sha256"]:
        raise ValueError("frozen predecessor tool changed: " + name)
    for dependency, expected in binding["dependencies"].items():
        if digest((ROOT / "scripts" / dependency).read_bytes()) != expected:
            raise ValueError("frozen predecessor dependency changed: " + dependency)


def require_btc_proofs(summary, checks, assessment, article, rule):
    if (
        not summary["success"]
        or not summary["sampled_cross_check_passed"]
        or not summary["combined_identity_evidence_satisfied"]
        or len(checks) != 7
        or not all(c["passed"] for c in checks.values())
        or not assessment["combined_identity_evidence_satisfied"]
        or article != assessment["dated_2019_notice"]
        or not article["clauses_verified"]
        or rule["proof_checks"] != assessment["prior_identity_checks"]
        or any(rule[k] != assessment[k] for k in ("scope_from", "scope_to_exclusive"))
        or not all(
            rule["proof_checks"][k]
            for k in ("historical_identity", "provider_identity", "venue_name", "token_contract")
        )
    ):
        raise ValueError("BTC combined identity evidence inconsistent")


def verify_btc_evidence(root, old_btc):
    summary = read_json(root / "summary.json")
    verify_output_hashes(root, summary)
    binding = read_json(root / "review/run_config.json")
    if binding != read_json(root / "contract/run_config.json") | {
        "input_hashes": binding["input_hashes"],
        "sources": binding["sources"],
        "failed_attempts": binding["failed_attempts"],
    }:
        raise ValueError("BTC audit contract/review mismatch")
    verify_tool(binding, "check_btc_public_api.py")
    if digest(btc_api.CONFIG.read_bytes()) != binding["plan_sha256"]:
        raise ValueError("BTC public API plan changed")
    for path, expected in binding["input_hashes"].items():
        if digest(repo_path(path).read_bytes()) != expected:
            raise ValueError("BTC audit predecessor input changed")
    seed = root / "capture_seed.json"
    if digest(seed.read_bytes()) != binding["capture_seed_sha256"]:
        raise ValueError("BTC capture seed changed")
    for label, expected in read_json(seed)["source_metadata_hashes"].items():
        if digest((root / "capture/raw" / (label + ".json")).read_bytes()) != expected:
            raise ValueError("BTC raw metadata changed")
    plan = read_json(btc_api.CONFIG)
    outcomes = read_json(root / "source_outcomes.json")
    if outcomes != binding["sources"] or len(outcomes) != 7:
        raise ValueError("BTC source outcomes changed")
    bodies = {}
    for source in plan["sources"]:
        label = source["id"]
        item = checked_source(root / "capture", label, source["url"])
        if (
            outcomes[label]["state"] != "available"
            or item is None
            or item[1] != outcomes[label]["metadata"]
        ):
            raise ValueError("BTC public response missing or changed")
        bodies[label] = item[0]
    archives = btc_api.load_archives(plan)
    windows = {w["id"]: w for w in plan["windows"]}
    checks = {
        "exchange_info": btc_api.api_check(
            btc_api.metadata_check, bodies["exchange_info"], plan["windows"][0]["start_ms"]
        )
    }
    for source in plan["sources"][1:]:
        label, kind = source["id"], source["kind"]
        window = windows[source["window"]]
        start, end = window["start_ms"], window["end_ms"]
        clock = "event_timestamp_ms" if kind == "funding" else "bar_open_ms"
        rows = [r for r in archives[(kind, window["start"][:7])] if start <= r[clock] < end]
        function = btc_api.compare_funding if kind == "funding" else btc_api.compare_bars
        args = () if kind == "funding" else (kind,)
        checks[label] = btc_api.api_check(function, bodies[label], rows, start, end, *args)
    if checks != read_json(root / "checks.json") or not all(c["passed"] for c in checks.values()):
        raise ValueError("BTC checks do not reproduce successfully")
    assessment = read_json(root / "btc_identity_assessment.json")
    _, article, _ = btc_api.article_check(
        (ROOT / "data/interim/early_identity_batch1_20261119/raw/future_eth.raw").read_bytes(),
        "360036964392",
        [
            "second perpetual contract",
            "how to switch from btc/usdt contract to eth/usdt contract",
            "2019/11/29",
        ],
    )
    rule = old_btc["mapping_record"]["mapping"]
    require_btc_proofs(summary, checks, assessment, article, rule)
    return assessment


def integrate_btc(previous, expected_sha, audit_provenance):
    rows = copy.deepcopy(previous)
    btc = next(r for r in rows if r["instrument_id"] == "BTCUSDT")
    old = btc["mapping_record"]
    if old["rule_sha256"] != expected_sha or fingerprint(old["mapping"]) != expected_sha:
        raise ValueError("BTC predecessor rule mismatch")
    if btc["identity_status"] != "pending_registered_evidence" or old["mapping"][
        "pending_gates"
    ] != ["venue_futures"]:
        raise ValueError("unexpected pending BTC gates")
    rule = copy.deepcopy(old["mapping"])
    rule["proof_checks"].update(
        venue_futures=True,
        public_api_sample_consistency=True,
        current_contract_identity=True,
        dated_2019_BTC_contract_reference=True,
    )
    rule.update(
        size_identity_join_allowed=True,
        pending_gates=[],
        mapping_basis="Combined prior numerical/name/history evidence, current BTCUSDT perpetual metadata, exact 2020 API/archive samples and dated2019 BTC contract reference; retrospective inference.",
    )
    registry = {"BTCUSDT": old}
    register_rule(
        registry,
        rule,
        audit_provenance,
        {
            "replaces_rule_sha256": expected_sha,
            "replacement_reason": "Registered combined BTC evidence replaces unavailable document-only gate;scope and all strict-eligibility limitations preserved.",
        },
    )
    btc["mapping_record"] = registry["BTCUSDT"]
    btc["identity_status"] = "corroborated_identity"
    btc["missing_requirements"] = []
    return rows


def week_row(identity, observation, reference):
    symbol = identity["instrument_id"]
    if observation["instrument_id"] != symbol or observation["reference_time_ms"] != reference:
        raise ValueError("weekly observation identity/time mismatch")
    if (
        observation["data_day"]
        != (datetime.fromtimestamp(reference / 1000, UTC).date() - timedelta(days=1)).isoformat()
    ):
        raise ValueError("weekly observation must be the previous UTC day")
    record = identity["mapping_record"]
    rule = record["mapping"] if record else None
    corroborated = identity["identity_status"] == "corroborated_identity" and bool(
        rule and rule["size_identity_join_allowed"]
    )
    in_scope = bool(
        rule
        and datetime.fromisoformat(rule["scope_from"]).timestamp() * 1000
        <= reference
        < datetime.fromisoformat(rule["scope_to_exclusive"]).timestamp() * 1000
    )
    conditions = {
        "price_history_not_ready_or_incomplete": bool(
            observation["price_history_diagnostic_candidate"]
        ),
        "identity_evidence_pending": corroborated,
        "outside_identity_scope": in_scope,
        "invalid_closing_observation": bool(observation["valid_closing_observation"]),
        "incomplete_trade_day": bool(observation["complete_trade_day"]),
        "composite_index": not observation["known_composite_index"],
        "known_settled": not observation["audit_at_or_after_confirmed_settlement"],
    }
    reasons = [name for name, passed in conditions.items() if not passed]
    eligible = not reasons
    fresh = bool(observation["funding_freshness_diagnostic"])
    return {
        "decision_date": datetime.fromtimestamp(reference / 1000, UTC).date().isoformat(),
        "reference_time_ms": reference,
        "data_day": observation["data_day"],
        "instrument_id": symbol,
        "price_history_candidate": conditions["price_history_not_ready_or_incomplete"],
        "identity_evidence_corroborated": corroborated,
        "decision_identity_in_scope": in_scope,
        "identity_scope_history_candidate": eligible,
        "funding_freshness_diagnostic": fresh,
        "identity_scope_history_with_fresh_funding": eligible and fresh,
        "identity_history_exclusion_reasons": reasons,
        "primary_identity_history_exclusion": reasons[0] if reasons else None,
        "funding_exclusion": "missing_or_stale_funding" if eligible and not fresh else None,
        "strict_trading_eligibility_established": False,
    }


def coverage(panel, identities, times):
    by_id = {r["instrument_id"]: r for r in identities}
    if len(by_id) != len(identities) or set(by_id) != set(panel):
        raise ValueError("identity/panel identifiers differ")
    if any(set(records) != set(times) for records in panel.values()):
        raise ValueError("weekly calendar coverage differs")
    detail, weeks = [], []
    for reference in times:
        batch = [week_row(by_id[s], panel[s][reference], reference) for s in sorted(panel)]
        detail.extend(batch)
        row = {"decision_date": batch[0]["decision_date"], "reference_time_ms": reference}
        for field in (
            "price_history_candidate",
            "identity_scope_history_candidate",
            "identity_scope_history_with_fresh_funding",
        ):
            names = [r["instrument_id"] for r in batch if r[field]]
            row[field + "_count"] = len(names)
            row[field + "_members"] = names
        row["primary_identity_history_exclusion_counts"] = dict(
            Counter(
                r["primary_identity_history_exclusion"]
                for r in batch
                if r["primary_identity_history_exclusion"]
            )
        )
        if sum(row["primary_identity_history_exclusion_counts"].values()) + row[
            "identity_scope_history_candidate_count"
        ] != len(by_id):
            raise ValueError("exclusion counts do not reconcile")
        row["strict_trading_eligibility_established"] = False
        weeks.append(row)
    return detail, weeks


def stats(weeks, field):
    values = [r[field + "_count"] for r in weeks]
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "maximum": max(values),
        "asset_weeks": sum(values),
        "nonempty_weeks": sum(v > 0 for v in values),
        "weeks_at_least20": sum(v >= 20 for v in values),
        "weeks_at_least30": sum(v >= 30 for v in values),
        "first_nonempty_week": next(
            (r["decision_date"] for r in weeks if r[field + "_count"] > 0), None
        ),
    }


def write_csv(path, rows):
    temporary = path.with_suffix(".csv.part")
    with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                    for k, v in row.items()
                }
            )
    temporary.replace(path)


def run(args):
    started = time.monotonic()
    plan = read_json(CONFIG)
    output = ROOT / "data/interim/early_weekly_universe" / args.version
    with exclusive_run(output / ".release.lock"):
        for path, expected in plan["inputs"].items():
            if digest(repo_path(path).read_bytes()) != expected:
                raise ValueError("frozen input changed: " + path)
        old_root = repo_path(plan["identity_root"])
        old_summary = read_json(old_root / "summary.json")
        verify_output_hashes(old_root, old_summary)
        old_binding = read_json(old_root / "run_config.json")
        verify_tool(old_binding, "run_early_identity.py")
        old = read_json(old_root / "asset_review.json")
        if (
            len(old) != plan["expected_identifiers"]
            or old_summary["supported_price_history_identifiers"]
            != plan["expected_prior_supported_history"]
            or sum(r["identity_status"] == "corroborated_identity" for r in old)
            != plan["expected_prior_corroborated"]
        ):
            raise ValueError("predecessor identity counts differ")
        old_btc = next(r for r in old if r["instrument_id"] == "BTCUSDT")
        audit_root = repo_path(plan["btc_audit_root"])
        assessment = verify_btc_evidence(audit_root, old_btc)
        panel, panel_hashes = inventory.load_panel()
        if any(old_binding[k] != v for k, v in panel_hashes.items()):
            raise ValueError("weekly panels differ from frozen predecessor")
        rows = integrate_btc(old, plan["replaces_btc_rule_sha256"], plan["btc_audit_root"])
        if any(a != b for a, b in zip(old, rows, strict=True) if a["instrument_id"] != "BTCUSDT"):
            raise ValueError("non-BTC identity changed")
        times = inventory.decision_times()
        if len(times) != plan["expected_weeks"]:
            raise ValueError("unexpected weekly calendar")
        detail, weeks = coverage(panel, rows, times)
        history_counts = Counter(r["instrument_id"] for r in detail if r["price_history_candidate"])
        if (
            sum(history_counts.values()) != old_summary["candidate_asset_weeks"]
            or any(
                history_counts[r["instrument_id"]] != r["price_history_candidate_weeks"]
                for r in rows
            )
            or sum(r["price_history_candidate_weeks"] > 0 for r in rows)
            != plan["expected_history_candidates"]
        ):
            raise ValueError("weekly history counts differ from predecessor")
        contract = {
            "plan_sha256": digest(CONFIG.read_bytes()),
            "script_sha256": digest(Path(__file__).read_bytes()),
            "dependencies": {
                name: digest((ROOT / "scripts" / name).read_bytes())
                for name in [
                    "check_btc_public_api.py",
                    "run_early_identity.py",
                    "inventory_early_size.py",
                    "acquire_usdm_universe.py",
                    "collect_cmc_weekly.py",
                ]
            },
            "frozen_inputs": plan["inputs"],
            **panel_hashes,
        }
        bind_run(output / "contract", contract)
        write_json(output / "asset_review.json", rows)
        write_json(output / "missing_evidence.json", [r for r in rows if r["missing_requirements"]])
        write_json(
            output / "btc_evidence_consumption.json",
            {
                "source": plan["btc_audit_root"],
                "assessment": assessment,
                "replaces_rule_sha256": plan["replaces_btc_rule_sha256"],
                "new_rule_sha256": next(r for r in rows if r["instrument_id"] == "BTCUSDT")[
                    "mapping_record"
                ]["rule_sha256"],
            },
        )
        write_json(output / "weekly_counts.json", weeks)
        write_csv(
            output / "asset_review.csv",
            [
                {
                    "instrument_id": r["instrument_id"],
                    "identity_status": r["identity_status"],
                    "price_history_candidate_weeks": r["price_history_candidate_weeks"],
                    "missing_requirements": r["missing_requirements"],
                }
                for r in rows
            ],
        )
        write_csv(output / "asset_weeks.csv", detail)
        write_csv(output / "weekly_counts.csv", weeks)
        fields = (
            "price_history_candidate",
            "identity_scope_history_candidate",
            "identity_scope_history_with_fresh_funding",
        )
        summary = {
            "success": True,
            "scope": "81early identifiers;2020 only",
            "identifiers": len(rows),
            "weekly_decisions": len(weeks),
            "asset_week_rows": len(detail),
            "identity_status_counts": dict(Counter(r["identity_status"] for r in rows)),
            "price_history_candidate_identifiers": sum(
                r["price_history_candidate_weeks"] > 0 for r in rows
            ),
            "supported_price_history_identifiers": sum(
                r["identity_status"] == "corroborated_identity"
                and r["price_history_candidate_weeks"] > 0
                for r in rows
            ),
            "coverage": {field: stats(weeks, field) for field in fields},
            "identity_scope_history_ever_members": sorted(
                {r["instrument_id"] for r in detail if r["identity_scope_history_candidate"]}
            ),
            "new_identity_release_written": True,
            "prior_releases_modified": False,
            "strict_trading_eligibility_established": False,
            "Size_publication_vintage_proven": False,
            "funding_payments_proven": False,
            "canonical_market_data_releases_modified": False,
            "source_http_requests_this_run": 0,
            "PnL_computed": False,
            "OOS_performance_inspected": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "output_hashes": {
                name: digest((output / name).read_bytes())
                for name in [
                    "asset_review.json",
                    "missing_evidence.json",
                    "btc_evidence_consumption.json",
                    "weekly_counts.json",
                    "asset_review.csv",
                    "asset_weeks.csv",
                    "weekly_counts.csv",
                ]
            },
        }
        write_json(output / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "summary"])
    parser.add_argument("--version", default="v20261120_001")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.version):
        raise ValueError("unsafe version")
    if args.action == "summary":
        root = ROOT / "data/interim/early_weekly_universe" / args.version
        summary = read_json(root / "summary.json")
        verify_output_hashes(root, summary)
        print(json.dumps(summary, sort_keys=True))
        return
    path = ROOT / "reports/acquisition" / ("early_weekly_universe_" + args.version + ".log")
    print("Log: " + str(path), flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        path.open("a", encoding="utf-8") as log,
        redirect_stdout(LogTee(sys.stdout, log)),
        redirect_stderr(LogTee(sys.stderr, log)),
    ):
        run(args)


if __name__ == "__main__":
    main()
