"""Validate ex-post identity decisions; this is not a trading-universe allowlist."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
FOLLOWUP = ROOT / "data/interim/identity_followup_20261118"
PRIOR = ROOT / "data/interim/contract_identity_review_20261118"


def utc(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise ValueError("decision boundary must explicitly use UTC")
    return result


def validate_policy(policy, population):
    start, end = utc(policy["research_window_from"]), utc(policy["research_window_to"])
    if start >= end:
        raise ValueError("invalid research window")
    whole = policy["whole_identifier_exclusions"]
    ids = [r["instrument_id"] for r in whole]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate whole-identifier decisions")
    for row in whole + policy["interval_exclusions"]:
        if (
            row["instrument_id"] not in population
            or not row["reason"]
            or not row["sources_checked"]
            or not row["readmit_if"]
        ):
            raise ValueError("incomplete/out-of-scope exclusion")
        if not row["scopes"] or not set(row["scopes"]) <= {"size_join", "regular_execution"}:
            raise ValueError("unexpected exclusion scope")
        if "from_utc" in row:
            a, b = utc(row["from_utc"]), utc(row["to_utc"])
            if not start <= a < b <= end:
                raise ValueError("invalid exclusion interval")
    updates = policy["vendor_updates"]
    if len({r["instrument_id"] for r in updates}) != len(updates):
        raise ValueError("duplicate vendor update")
    for row in updates:
        if row["instrument_id"] not in population or row["automatic_join_approved"] is not False:
            raise ValueError("unexpected approval or update outside scope")
    rejected = {
        (r["instrument_id"], r["vendor_asset_id"]) for r in policy["rejected_vendor_associations"]
    }
    if any((r["instrument_id"], r["proposed_vendor_asset_id"]) in rejected for r in updates):
        raise ValueError("retained/rejected vendor contradiction")
    if policy["sats"]["automatic_cross_ID_splicing"] or policy["sats"]["cap_multiplier"] != 1:
        raise ValueError("SATS cannot be spliced or have USD cap rescaled")
    if (
        policy["historical_joins_approved"] != 0
        or policy["point_in_time_ready"]
        or policy["OOS_performance_inspected"]
    ):
        raise ValueError("unexpected readiness or performance flag")
    for reset in policy["feature_state_resets"]:
        if reset["instrument_id"] not in population or not start <= utc(reset["at_utc"]) < end:
            raise ValueError("invalid reset")


def exclusion_reasons(policy, instrument, at_utc, scope):
    """Negative gate only. An empty result never grants trading or join eligibility."""
    if scope not in {"size_join", "regular_execution"}:
        raise ValueError("unknown scope")
    stamp = utc(at_utc)
    if not utc(policy["research_window_from"]) <= stamp < utc(policy["research_window_to"]):
        return ["outside_reviewed_research_window"]
    reasons = [
        r["reason"]
        for r in policy["whole_identifier_exclusions"]
        if r["instrument_id"] == instrument and scope in r["scopes"]
    ]
    reasons += [
        r["reason"]
        for r in policy["interval_exclusions"]
        if r["instrument_id"] == instrument
        and scope in r["scopes"]
        and utc(r["from_utc"]) <= stamp < utc(r["to_utc"])
    ]
    return reasons


def build(config_path, output):
    policy = read_json(config_path)
    prior_summary = read_json(PRIOR / "review_002/summary.json")
    prior_config = ROOT / "config/contract_identity_evidence_20261118.json"
    if (
        not prior_summary["success"]
        or digest(prior_config.read_bytes()) != prior_summary["inputs"]["config_sha256"]
    ):
        raise ValueError("prior review/config mismatch")
    records = read_json(prior_config)["records"]
    population = {r["instrument_id"] for r in records}
    validate_policy(policy, population)
    source_hashes = {}
    for code, expected in prior_summary["inputs"]["sources"].items():
        body = (PRIOR / "raw" / (code + ".raw")).read_bytes()
        if digest(body) != expected:
            raise ValueError("prior official source integrity failure")
        source_hashes[code] = expected
    audit_root = FOLLOWUP / "audit_003"
    audit_config = read_json(audit_root / "run_config.json")
    if not read_json(audit_root / "summary.json")["success"]:
        raise ValueError("follow-up audit incomplete")
    if audit_config["tool_sha256"] != digest(
        (ROOT / "scripts/check_identity_followup.py").read_bytes()
    ):
        raise ValueError("follow-up tool hash mismatch")
    if audit_config["source_config_sha256"] != digest(
        (ROOT / "config/identity_followup_sources_20261118.json").read_bytes()
    ):
        raise ValueError("follow-up source config mismatch")
    sources = read_json(audit_root / "source_assertions.json")
    for key, expected in audit_config["verified_source_hashes"].items():
        if digest((FOLLOWUP / "raw" / (key + ".raw")).read_bytes()) != expected:
            raise ValueError("follow-up source integrity failure")
    for row in policy["whole_identifier_exclusions"] + policy["interval_exclusions"]:
        if any(ref not in sources and ref not in source_hashes for ref in row["sources_checked"]):
            raise ValueError("decision refers to unchecked evidence")
    vendor_history_path = (
        ROOT / "data/interim/cmc_identity_audit_002_20261118/vendor_identity_history.json"
    )
    history = {r["vendor_asset_id"]: r["observed_dates"] for r in read_json(vendor_history_path)}
    enriched = []
    for row in policy["vendor_updates"]:
        identity = sources[row["source_id"]]["identity"]
        if identity["id"] != row["proposed_vendor_asset_id"]:
            raise ValueError("vendor proposal differs from verified vendor page")
        enriched.append(
            {
                **row,
                "vendor_name": identity["name"],
                "contracts": identity["contracts"],
                "snapshot_dates_with_this_ID": history.get(identity["id"], 0),
                "historical_chain_mapping_approved": False,
            }
        )
    sun = sources["cmc_sun"]["identity"]
    if sun["id"] != 10529 or not sources["sun_launch"]["launch_assertion_verified"]:
        raise ValueError("SUN correction lacks evidence")
    address = "TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S"
    if not any(p["contractAddress"] == address for p in sun["contracts"]):
        raise ValueError("SUN contract crosscheck failed")
    excerpt_path = FOLLOWUP / policy["sats"]["evidence_file"]
    excerpt = read_json(excerpt_path)
    if (
        excerpt["reported_UCID"] != 28683
        or "same asset in different denominations" not in excerpt["excerpt"]
    ):
        raise ValueError("SATS cached rendered evidence mismatch")
    whole = {r["instrument_id"] for r in policy["whole_identifier_exclusions"]}
    cases = [
        {
            "instrument_id": instrument,
            "decision": "temporarily_exclude_size_join"
            if instrument in whole
            else "retain_identity_candidate",
            "historical_join_approved": False,
            "historical_strategy_eligible": False,
            "decision_date": policy["decision_date"],
            "historical_availability_basis": "ex_post_review_only",
            "whole_scope_reason": next(
                (
                    r
                    for r in policy["whole_identifier_exclusions"]
                    if r["instrument_id"] == instrument
                ),
                None,
            ),
            "interval_exclusions": [
                r for r in policy["interval_exclusions"] if r["instrument_id"] == instrument
            ],
        }
        for instrument in sorted(population)
    ]
    inputs = {
        "tool_sha256": digest(Path(__file__).read_bytes()),
        "policy_sha256": digest(config_path.read_bytes()),
        "prior_review_summary_sha256": digest((PRIOR / "review_002/summary.json").read_bytes()),
        "audit_run_config_sha256": digest((audit_root / "run_config.json").read_bytes()),
        "audit_source_assertions_sha256": digest(
            (audit_root / "source_assertions.json").read_bytes()
        ),
        "vendor_history_sha256": digest(vendor_history_path.read_bytes()),
        "rendered_excerpt_sha256": digest(excerpt_path.read_bytes()),
    }
    bind_run(output, inputs)
    write_json(output / "decisions.json", cases)
    write_json(output / "vendor_resolution_updates.json", enriched)
    write_json(output / "policy.json", policy)
    summary = {
        "success": True,
        "errors": [],
        "priority_identifiers": len(cases),
        "decision_counts": dict(Counter(r["decision"] for r in cases)),
        "whole_size_join_exclusions": sorted(whole),
        "interval_exclusions": len(policy["interval_exclusions"]),
        "vendor_updates": len(enriched),
        "new_IDs_without_snapshot_history": sum(
            r["snapshot_dates_with_this_ID"] == 0 for r in enriched
        ),
        "historical_joins_approved": 0,
        "historical_eligible_universe_ready": False,
        "OOS_performance_inspected": False,
    }
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/identity_decisions_20261118.json"
    )
    parser.add_argument("--output", type=Path, default=FOLLOWUP / "decisions")
    args = parser.parse_args()
    with exclusive_run(args.output / ".decisions.lock"):
        build(args.config, args.output)


if __name__ == "__main__":
    main()
