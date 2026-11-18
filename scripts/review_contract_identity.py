"""Capture official identity evidence and validate proposed, non-executable mappings."""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from collect_cmc_weekly import Downloader, checked_source, raw_bytes, write_source
from review_usdm_lifecycle import text_nodes

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data/interim/cmc_identity_audit_002_20261118"
SEED = ROOT / "data/interim/usdm_universe/lifecycle_review_20261118/sources"
LIMIT = 64 * 1024**2


def article_url(code):
    if not re.fullmatch(r"[a-f0-9]{32}", code):
        raise ValueError("invalid official article code")
    return (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode="
        + code
    )


def article_text(body, expected_code=None):
    payload = json.loads(body)
    if not payload.get("success") or not payload.get("data", {}).get("body"):
        raise ValueError("official CMS returned no article")
    item = payload["data"]
    if expected_code is not None and item.get("code") != expected_code:
        raise ValueError("official CMS article identity mismatch")
    return item, " ".join(text_nodes(json.loads(item["body"])))


def capture(config, output):
    codes = sorted(config["sources"])
    if len(codes) != len(set(codes)) or len(codes) > 60:
        raise ValueError("source budget exceeded")
    paused = output / "access_pause.json"
    if paused.exists() and time.time() < read_json(paused)["not_before_epoch"]:
        raise ValueError("access cooldown active")
    if raw_bytes(output) > LIMIT:
        raise ValueError("raw budget exceeded")
    downloader = Downloader(output, LIMIT)
    hits = 0
    for number, code in enumerate(codes, 1):
        url = article_url(code)
        previous = checked_source(output, code, url)
        if previous is None and (SEED / (code + ".json")).exists():
            meta = read_json(SEED / (code + ".json"))
            body = (SEED / (code + ".raw")).read_bytes()
            if meta["sha256"] != digest(body) or meta["bytes"] != len(body):
                raise ValueError("seed integrity failure")
            if meta["retrieval_url"] != url or raw_bytes(output) + len(body) > LIMIT:
                raise ValueError("seed URL/budget failure")
            write_source(
                output,
                code,
                body,
                {
                    "url": url,
                    "status": 200,
                    "sha256": digest(body),
                    "bytes": len(body),
                    "retrieved_at": meta["retrieved_at"],
                    "reused_verified_lifecycle_source": True,
                },
            )
        body, _, cached = downloader.get(code, url)
        article_text(body, code)
        hits += int(cached)
        print(f"Identity evidence {number}/{len(codes)}; HTTP={downloader.requests}", flush=True)
    write_json(
        output / "capture_summary.json",
        {
            "success": True,
            "sources": len(codes),
            "cache_hits": hits,
            "http_requests": downloader.requests,
            "raw_bytes": raw_bytes(output),
        },
    )


def timestamp(value):
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("boundary must explicitly use UTC")
    return parsed


def validate_record(record, sources, vendors):
    if not record["assertions"] or not record["proposed_episodes"]:
        raise ValueError("review must contain evidence and episode proposals")
    assertions = {a["assertion_id"]: a for a in record["assertions"]}
    if len(assertions) != len(record["assertions"]):
        raise ValueError("duplicate assertion")
    for assertion in assertions.values():
        evidence = assertion["evidence"]
        if not evidence:
            raise ValueError("assertion has no source evidence")
        for ref in evidence:
            if ref["article_code"] not in sources or not ref["terms"]:
                raise ValueError("missing source/terms")
            content = sources[ref["article_code"]]["text"].casefold()
            if any(term.casefold() not in content for term in ref["terms"]):
                raise ValueError(f"evidence term missing: {assertion['assertion_id']}")
    episodes = record["proposed_episodes"]
    for episode in episodes:
        start, end = timestamp(episode["effective_from"]), timestamp(episode["effective_to"])
        if start is not None and end is not None and start >= end:
            raise ValueError("invalid episode interval")
        if not episode["assertion_ids"] or any(
            a not in assertions for a in episode["assertion_ids"]
        ):
            raise ValueError("episode lacks evidence assertions")
        if start is not None and episode.get("start_assertion_id") not in episode["assertion_ids"]:
            raise ValueError("start has no cited boundary assertion")
        if end is not None and episode.get("end_assertion_id") not in episode["assertion_ids"]:
            raise ValueError("end has no cited boundary assertion")
        for value, key, event in (
            (start, "start_assertion_id", "launch"),
            (end, "end_assertion_id", "automatic_settlement"),
        ):
            if value is not None:
                assertion = assertions[episode[key]]
                if (
                    timestamp(assertion.get("effective_at")) != value
                    or assertion.get("event_type") != event
                ):
                    raise ValueError("boundary does not match event evidence")
        vendor = episode["proposed_vendor_asset_id"]
        if vendor is not None and vendor not in vendors:
            raise ValueError("vendor ID absent from captured history")
        if vendor is not None and vendor in record.get("do_not_join_vendor_asset_ids", []):
            raise ValueError("rejected vendor identity cannot be proposed")
        if any(v not in vendors for v in episode.get("candidate_vendor_asset_ids", [])):
            raise ValueError("candidate vendor ID absent from captured history")
        units = episode["underlying_tokens_per_price_unit"]
        if units is not None:
            if type(units) is not int or units <= 0:
                raise ValueError("invalid units")
            if episode.get("unit_assertion_id") not in episode["assertion_ids"]:
                raise ValueError("unit convention lacks evidence")
            if (
                assertions[episode["unit_assertion_id"]].get("underlying_tokens_per_price_unit")
                != units
            ):
                raise ValueError("unit assertion does not match convention")
        if not episode["unresolved"]:
            raise ValueError("partial review must preserve unresolved gates")
    for index, left in enumerate(episodes):
        for right in episodes[index + 1 :]:
            # Unknown limits are not implicitly -/+infinity. Different identities
            # with unproven boundaries cannot become automatically executable.
            a, b = timestamp(left["effective_from"]), timestamp(left["effective_to"])
            c, d = timestamp(right["effective_from"]), timestamp(right["effective_to"])
            if (
                (a and b and c and a <= c < b)
                or (c and d and a and c <= a < d)
                or (a and c and a == c)
            ):
                raise ValueError("proposed episodes overlap")
    return {
        **record,
        "review_status": "partial_evidence_supported",
        "historical_join_approved": False,
        "historical_strategy_eligible": False,
        "point_in_time_ready": False,
        "causal_available_at": None,
        "vendor_identity_interpretation": "human proposed association; captured ID labels corroborate names only",
    }


def build(config_path, output):
    config = read_json(config_path)
    source_reports, sources = {}, {}
    for code in config["sources"]:
        body, provenance, _ = checked_source(output, code, article_url(code))
        article, content = article_text(body, code)
        source_reports[code] = {
            **provenance,
            "title": article["title"],
            "source_url": "https://www.binance.com/en/support/announcement/detail/" + code,
            "cms_publish_date_raw": article.get("publishDate"),
            "cms_last_update_time_raw": article.get("lastUpdateTime"),
            "historical_content_version_proven": False,
            "causal_available_at": None,
        }
        sources[code] = {"text": content}
    queue_path, vendor_path = (
        AUDIT / "identity_review_queue.json",
        AUDIT / "vendor_identity_history.json",
    )
    audit_summary = read_json(AUDIT / "summary.json")
    if not audit_summary["success"]:
        raise ValueError("input audit incomplete")
    queue, vendor_rows = read_json(queue_path), read_json(vendor_path)
    vendors = {row["vendor_asset_id"] for row in vendor_rows}
    priority = {
        q["instrument_id"]
        for q in queue
        if q["candidate_ID_ambiguity"]
        or q["known_identity_reuse"]
        or "possible_scaled_contract_requires_evidence" in q["review_flags"]
    }
    ids = [r["instrument_id"] for r in config["records"]]
    if len(ids) != len(set(ids)) or set(ids) != priority:
        raise ValueError("review scope does not match frozen priority queue")
    reviewed = [validate_record(r, sources, vendors) for r in config["records"]]
    inputs = {
        "config_sha256": digest(config_path.read_bytes()),
        "tool_sha256": digest(Path(__file__).read_bytes()),
        "queue_sha256": digest(queue_path.read_bytes()),
        "vendor_history_sha256": digest(vendor_path.read_bytes()),
        "audit_summary_sha256": digest((AUDIT / "summary.json").read_bytes()),
        "sources": {k: v["sha256"] for k, v in source_reports.items()},
    }
    derived = output / "review_002"
    bind_run(derived, inputs)
    by_id = {r["instrument_id"]: r for r in reviewed}
    missing = []
    for q in queue:
        if q["candidates_for_manual_review_only"]:
            continue
        flags = []
        if q["instrument_id"] in by_id:
            flags.append("priority_identity_evidence_in_separate_review")
        if "possible_scaled_contract_requires_evidence" in q["review_flags"]:
            flags.append("possible_scaled_contract_not_automatically_stripped")
        if q["current_noncoin_annotation"]:
            flags.append("current_noncoin_annotation_only")
        if q["known_identity_reuse"]:
            flags.append("known_identity_reuse")
        missing.append(
            {
                "instrument_id": q["instrument_id"],
                "diagnostic_leads": flags,
                "absence_reason": "unresolved_first_page_or_identity_gap",
                "historical_strategy_eligible": False,
            }
        )
    write_json(derived / "sources.json", source_reports)
    write_json(derived / "proposed_episode_map.json", reviewed)
    write_json(derived / "missing_candidate_classification.json", missing)
    summary = {
        "success": True,
        "errors": [],
        "priority_identifiers_reviewed": len(reviewed),
        "official_sources_verified": len(sources),
        "assertions_verified": sum(len(r["assertions"]) for r in reviewed),
        "proposed_episodes": sum(len(r["proposed_episodes"]) for r in reviewed),
        "episodes_with_vendor_ID_proposals": sum(
            e["proposed_vendor_asset_id"] is not None
            for r in reviewed
            for e in r["proposed_episodes"]
        ),
        "missing_candidate_identifiers": len(missing),
        "missing_diagnostic_lead_counts": dict(
            Counter(f for r in missing for f in r["diagnostic_leads"])
        ),
        "historical_joins_approved": 0,
        "historical_eligible_universe_ready": False,
        "point_in_time_ready": False,
        "OOS_performance_inspected": False,
        "inputs": inputs,
    }
    write_json(derived / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "inputs"}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["capture", "build"])
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/contract_identity_evidence_20261118.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/interim/contract_identity_review_20261118"
    )
    args = parser.parse_args()
    with exclusive_run(args.output / ".review.lock"):
        if args.action == "capture":
            capture(read_json(args.config), args.output)
        else:
            build(args.config, args.output)


if __name__ == "__main__":
    main()
