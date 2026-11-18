"""Offline source reconciliation and lexical coverage; no approved identity joins."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from check_research_inputs import parse_snapshot
from collect_cmc_weekly import CalendarLinks, checked_source, mapping_review, requested_dates

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_verified(source, lifecycle):
    """Verify original evidence, including a fresh metadata-only parse of raw HTML."""
    plan_path = source / "plan.json"
    plan = read_json(plan_path)
    dates = requested_dates()
    require(plan["requested_dates"] == dates, "calendar does not match registered range")
    require(plan["expected_dates"] == len(dates), "calendar count mismatch")
    require(plan["listed_requested_dates"] == dates, "calendar listing incomplete")
    require(not plan["unlisted_requested_dates"], "unlisted dates")
    calendar, _, _ = checked_source(source, "calendar", "https://coinmarketcap.com/historical/")
    links = CalendarLinks()
    links.feed(calendar.decode("utf-8"))
    require(all(d in links.dates for d in dates), "source calendar listing incomplete")
    require(read_json(source / "raw/calendar.json") == plan["calendar_source"], "calendar source")
    full = source / "full"
    summary, config = read_json(full / "summary.json"), read_json(full / "run_config.json")
    require(
        summary["success"] and summary["full_scope"] and not summary["errors"], "run incomplete"
    )
    ledger_path = lifecycle / "identity_ledger.json"
    ledger_hash = digest(ledger_path.read_bytes())
    lifecycle_summary = read_json(lifecycle / "summary.json")
    require(
        lifecycle_summary["success"] and lifecycle_summary["ledger_sha256"] == ledger_hash,
        "ledger hash",
    )
    expected = {
        "schema": 1,
        "selected_dates": dates,
        "plan_sha256": digest(plan_path.read_bytes()),
        "ledger_sha256": ledger_hash,
        "tool_sha256": digest((ROOT / "scripts/collect_cmc_weekly.py").read_bytes()),
        "parser_sha256": digest((ROOT / "scripts/check_research_inputs.py").read_bytes()),
    }
    require(config == expected and summary["inputs"] == config, "configuration mismatch")
    identities = read_json(ledger_path)
    require(
        len({x["instrument_id"] for x in identities}) == len(identities), "duplicate instrument"
    )
    reports, rows = [], []
    for number, label in enumerate(dates, 1):
        body, provenance, _ = checked_source(
            source, label, "https://coinmarketcap.com/historical/" + label + "/"
        )
        target = full / "partitions" / (label + ".json")
        saved = read_json(target)
        report = {
            "date": label,
            "rows": len(saved),
            "source_sha256": provenance["sha256"],
            "parsed_sha256": digest(target.read_bytes()),
        }
        require(report == read_json(full / "index" / (label + ".json")), "partition integrity")
        fresh = parse_snapshot(body, label)
        for row in fresh:
            row["source"] = provenance
        require(saved == fresh, "raw/parsed content mismatch")
        rows.extend(saved)
        reports.append(report)
        if number % 50 == 0 or number == len(dates):
            print(f"Verified source/parsed {number}/{len(dates)}", file=sys.stderr, flush=True)
    require(reports == read_json(full / "date_coverage.json"), "date coverage mismatch")
    review = mapping_review(identities, rows)
    require(review == read_json(full / "mapping_review.json"), "mapping review mismatch")
    vendor_counts = Counter(r["vendor_asset_id"] for r in rows)
    require(
        read_json(full / "vendor_ID_coverage.json")
        == {str(k): v for k, v in sorted(vendor_counts.items())},
        "vendor coverage mismatch",
    )
    counts = {
        "planned_dates": len(dates),
        "verified_dates": len(dates),
        "rows": len(rows),
        "distinct_vendor_IDs": len(vendor_counts),
        "identifiers_reviewed": len(identities),
        "identifiers_with_lexical_candidates": sum(
            bool(x["candidates_for_manual_review_only"]) for x in review
        ),
        "ambiguous_candidate_identifiers": sum(x["candidate_ID_ambiguity"] for x in review),
        "approved_historical_mappings": 0,
    }
    require(all(summary[k] == v for k, v in counts.items()), "summary count mismatch")
    for flag in (
        "historical_eligible_universe_ready",
        "point_in_time_ready",
        "all_asset_coverage_proven",
        "OOS_performance_inspected",
    ):
        require(summary[flag] is False, "unexpected readiness/performance flag")
    return (
        identities,
        rows,
        review,
        {
            **expected,
            "acquisition_summary_sha256": digest((full / "summary.json").read_bytes()),
            "date_coverage_sha256": digest((full / "date_coverage.json").read_bytes()),
            "mapping_review_sha256": digest((full / "mapping_review.json").read_bytes()),
        },
    )


def token(identity):
    return (identity.get("current_product_metadata") or {}).get("baseAsset") or identity[
        "instrument_id"
    ].removesuffix("USDT")


def archive_overlap(identity, label):
    bounds = identity.get("archive_bounds", {}).get("trade")
    if not bounds or not bounds.get("first_month") or not bounds.get("last_month"):
        return False
    month = label[:4] + "-" + label[4:6]
    return bounds["first_month"] <= month <= bounds["last_month"]


def coverage(identities, rows):
    by_date = defaultdict(lambda: defaultdict(set))
    for row in rows:
        by_date[row["snapshot_date"]][row["symbol"].casefold()].add(row["vendor_asset_id"])
    result = []
    for label, symbols in sorted(by_date.items()):
        item = {
            "date": label,
            "denominator_note": "ex-post archive month span; NOT eligible universe",
        }
        for name, population in (
            ("all_identifiers", identities),
            ("archive_month_overlap", [i for i in identities if archive_overlap(i, label)]),
        ):
            counts = Counter()
            for identity in population:
                count = len(symbols[token(identity).casefold()])
                counts[
                    "absent_unknown"
                    if count == 0
                    else "single_candidate"
                    if count == 1
                    else "multiple_candidates"
                ] += 1
            item[name] = {
                "denominator": len(population),
                **{
                    key: counts[key]
                    for key in ("absent_unknown", "single_candidate", "multiple_candidates")
                },
            }
        result.append(item)
    return result


def review_queue(identities, rows, review):
    by_instrument = {r["instrument_id"]: r for r in review}
    dates = sorted({r["snapshot_date"] for r in rows})
    queue = []
    for identity in identities:
        item = dict(by_instrument[identity["instrument_id"]])
        candidates = item["candidates_for_manual_review_only"]
        observed = {d for c in candidates for d in c["observed_dates"]}
        archive_dates = [d for d in dates if archive_overlap(identity, d)]
        flags = []
        if item["candidate_ID_ambiguity"]:
            flags.append("multiple_vendor_IDs_across_history")
        if identity["known_identity_reuse"]:
            flags.append("known_contract_identity_reuse")
        if re.match(r"^(?:1000[0]*|1M)(?=[A-Z])", token(identity)):
            flags.append("possible_scaled_contract_requires_evidence")
        if identity.get("current_noncoin_annotation"):
            flags.append("current_noncoin_annotation_not_historical_classification")
        if not candidates:
            flags.append("no_literal_candidate_in_sampled_first_pages")
        bounds = identity.get("archive_bounds", {}).get("trade") or {}
        if not bounds.get("first_month") or not bounds.get("last_month"):
            flags.append("trade_archive_bounds_missing_not_in_overlap_denominator")
        item.update(
            {
                "review_flags": flags,
                "archive_month_overlap_dates": len(archive_dates),
                "lexical_present_overlap_dates": sum(d in observed for d in archive_dates),
                "absent_unknown_overlap_dates": sum(d not in observed for d in archive_dates),
                "archive_bounds_are_ex_post_not_lifecycle": True,
                "evidence_required": [
                    "dated_exchange_underlying_and_episode_boundaries",
                    "dated_vendor_identity_and_migration",
                    "contract_units",
                    "publication_time_and_content_vintage",
                ],
                "review_decision": "unreviewed",
                "approved_episodes": [],
            }
        )
        queue.append(item)
    return queue


def vendor_histories(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["vendor_asset_id"]].append(row)
    result = []
    for vendor_id, found in sorted(grouped.items()):
        appearances = [
            {
                "date": r["snapshot_date"],
                "symbol": r["symbol"],
                "name": r["name"],
                "slug": r["slug"],
            }
            for r in sorted(found, key=lambda x: x["snapshot_date"])
        ]
        result.append(
            {
                "vendor_asset_id": vendor_id,
                "observed_dates": len(found),
                "symbols": sorted({r["symbol"] for r in found}),
                "names": sorted({r["name"] for r in found}),
                "appearances": appearances,
                "continuity_verified": False,
            }
        )
    return result


def run(args):
    identities, rows, review, inputs = load_verified(args.source, args.lifecycle)
    inputs["audit_tool_sha256"] = digest(Path(__file__).read_bytes())
    bind_run(args.output, inputs)
    weekly = coverage(identities, rows)
    queue, vendors = review_queue(identities, rows, review), vendor_histories(rows)
    write_json(args.output / "weekly_lexical_coverage.json", weekly)
    write_json(args.output / "identity_review_queue.json", queue)
    write_json(args.output / "vendor_identity_history.json", vendors)
    flags = Counter(flag for item in queue for flag in item["review_flags"])
    yearly = []
    for year in sorted({w["date"][:4] for w in weekly}):
        selected = [w for w in weekly if w["date"].startswith(year)]
        aggregate = {
            key: sum(w["archive_month_overlap"][key] for w in selected)
            for key in ("denominator", "single_candidate", "multiple_candidates", "absent_unknown")
        }
        yearly.append({"year": year, "weeks": len(selected), "ex_post_instrument_weeks": aggregate})
    write_json(args.output / "yearly_lexical_coverage.json", yearly)
    summary = {
        "success": True,
        "errors": [],
        "dates_verified": len(weekly),
        "rows_verified": len(rows),
        "identifiers_reviewed": len(queue),
        "vendor_IDs": len(vendors),
        "identifiers_with_literal_candidates": sum(
            bool(r["candidates_for_manual_review_only"]) for r in queue
        ),
        "review_flag_counts": dict(flags),
        "vendor_IDs_with_symbol_changes": sum(len(v["symbols"]) > 1 for v in vendors),
        "rows_with_unproven_availability_or_vintage": sum(
            r["available_at"] is None or not r["historical_content_version_proven"] for r in rows
        ),
        "approved_historical_mappings": 0,
        "historical_eligible_universe_ready": False,
        "point_in_time_ready": False,
        "all_asset_coverage_proven": False,
        "OOS_performance_inspected": False,
        "inputs": inputs,
    }
    write_json(args.output / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/interim/cmc_weekly_20261118")
    parser.add_argument(
        "--lifecycle",
        type=Path,
        default=ROOT / "data/interim/usdm_universe/lifecycle_review_20261118",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/interim/cmc_identity_audit_002_20261118"
    )
    args = parser.parse_args()
    with exclusive_run(args.output / ".audit.lock"):
        run(args)


if __name__ == "__main__":
    main()
