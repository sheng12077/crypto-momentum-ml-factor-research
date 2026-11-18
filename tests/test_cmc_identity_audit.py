from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acquire_usdm_universe import digest, read_json, write_json  # noqa: E402
from audit_cmc_identity import archive_overlap, coverage, load_verified, review_queue, run  # noqa: E402
from collect_cmc_weekly import mapping_review, write_source  # noqa: E402


def identity(symbol, base=None):
    return {
        "instrument_id": symbol + "USDT",
        "known_identity_reuse": False,
        "current_product_metadata": {"baseAsset": base or symbol},
        "archive_bounds": {"trade": {"first_month": "2021-01", "last_month": "2021-01"}},
    }


def fixture(root):
    source, lifecycle = root / "source", root / "lifecycle"
    ledger = [identity("BTC"), identity("1000PEPE"), identity("NONE")]
    write_json(lifecycle / "identity_ledger.json", ledger)
    ledger_hash = digest((lifecycle / "identity_ledger.json").read_bytes())
    write_json(lifecycle / "summary.json", {"success": True, "ledger_sha256": ledger_hash})
    label = "20210103"
    calendar = b'<a href="/historical/20210103/">date</a>'
    calendar_meta = {
        "status": 200,
        "url": "https://coinmarketcap.com/historical/",
        "sha256": digest(calendar),
        "bytes": len(calendar),
    }
    write_source(source, "calendar", calendar, calendar_meta)
    plan = {
        "requested_dates": [label],
        "listed_requested_dates": [label],
        "expected_dates": 1,
        "unlisted_requested_dates": [],
        "calendar_source": calendar_meta,
    }
    write_json(source / "plan.json", plan)
    raw_row = {
        "id": 1,
        "name": "Bitcoin",
        "symbol": "BTC",
        "slug": "bitcoin",
        "circulatingSupply": "100",
        "quote": {"USD": {"marketCap": "12345.1234567", "lastUpdated": "2021-01-03T00:00:00Z"}},
    }
    state = {"cryptocurrency": {"listingHistorical": {"data": [raw_row]}}}
    body = (
        '<title>Historical Snapshot - 03 January 2021</title><script id="__NEXT_DATA__">'
        + json.dumps({"props": {"initialState": json.dumps(state)}})
        + "</script>"
    ).encode()
    provenance = {
        "status": 200,
        "url": "https://coinmarketcap.com/historical/20210103/",
        "sha256": digest(body),
        "bytes": len(body),
    }
    write_source(source, label, body, provenance)
    from check_research_inputs import parse_snapshot

    rows = parse_snapshot(body, label)
    rows[0]["source"] = provenance
    full = source / "full"
    target = full / "partitions" / (label + ".json")
    write_json(target, rows)
    index = {
        "date": label,
        "rows": 1,
        "source_sha256": digest(body),
        "parsed_sha256": digest(target.read_bytes()),
    }
    write_json(full / "index" / (label + ".json"), index)
    write_json(full / "date_coverage.json", [index])
    write_json(full / "vendor_ID_coverage.json", {"1": 1})
    write_json(full / "mapping_review.json", mapping_review(ledger, rows))
    config = {
        "schema": 1,
        "selected_dates": [label],
        "ledger_sha256": ledger_hash,
        "plan_sha256": digest((source / "plan.json").read_bytes()),
        "tool_sha256": digest((ROOT / "scripts/collect_cmc_weekly.py").read_bytes()),
        "parser_sha256": digest((ROOT / "scripts/check_research_inputs.py").read_bytes()),
    }
    write_json(full / "run_config.json", config)
    write_json(
        full / "summary.json",
        {
            "success": True,
            "full_scope": True,
            "errors": [],
            "inputs": config,
            "planned_dates": 1,
            "verified_dates": 1,
            "rows": 1,
            "distinct_vendor_IDs": 1,
            "identifiers_reviewed": 3,
            "identifiers_with_lexical_candidates": 1,
            "ambiguous_candidate_identifiers": 0,
            "approved_historical_mappings": 0,
            "historical_eligible_universe_ready": False,
            "point_in_time_ready": False,
            "all_asset_coverage_proven": False,
            "OOS_performance_inspected": False,
        },
    )
    return Namespace(source=source, lifecycle=lifecycle, output=root / "output")


class IdentityAuditTests(unittest.TestCase):
    def test_missing_or_null_trade_bounds_do_not_claim_overlap(self):
        for bounds in (
            {},
            {"first_month": None, "last_month": None},
            {"first_month": "2021-01", "last_month": None},
        ):
            item = identity("BTC")
            item["archive_bounds"]["trade"] = bounds
            self.assertFalse(archive_overlap(item, "20210103"))
            rows = [
                {
                    "snapshot_date": "20210103",
                    "symbol": "BTC",
                    "vendor_asset_id": 1,
                    "name": "Bitcoin",
                }
            ]
            weekly = coverage([item], rows)[0]
            self.assertEqual(weekly["all_identifiers"]["denominator"], 1)
            self.assertEqual(weekly["archive_month_overlap"]["denominator"], 0)
            queue = review_queue([item], rows, mapping_review([item], rows))
            self.assertIn(
                "trade_archive_bounds_missing_not_in_overlap_denominator", queue[0]["review_flags"]
            )

    def test_offline_run_and_resume_keep_readiness_false(self):
        with tempfile.TemporaryDirectory() as directory:
            args = fixture(Path(directory))
            with (
                patch("audit_cmc_identity.requested_dates", return_value=["20210103"]),
                patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")),
                redirect_stdout(io.StringIO()),
            ):
                run(args)
                first = (args.output / "summary.json").read_bytes()
                run(args)
            self.assertEqual(first, (args.output / "summary.json").read_bytes())
            summary = read_json(args.output / "summary.json")
            self.assertTrue(summary["success"])
            self.assertFalse(summary["point_in_time_ready"])
            self.assertEqual(summary["approved_historical_mappings"], 0)
            queue = read_json(args.output / "identity_review_queue.json")
            self.assertIn("possible_scaled_contract_requires_evidence", queue[1]["review_flags"])
            self.assertEqual(queue[1]["approved_episodes"], [])

    def test_tampering_is_rejected_without_repair(self):
        cases = ["raw", "parsed", "config", "ledger", "mapping", "summary"]
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                args = fixture(Path(directory))
                target = {
                    "raw": args.source / "raw/20210103.raw",
                    "parsed": args.source / "full/partitions/20210103.json",
                    "config": args.source / "full/run_config.json",
                    "ledger": args.lifecycle / "identity_ledger.json",
                    "mapping": args.source / "full/mapping_review.json",
                    "summary": args.source / "full/summary.json",
                }[case]
                if case == "raw":
                    target.write_bytes(b"corrupt")
                elif case == "config":
                    value = read_json(target)
                    value["parser_sha256"] = "changed"
                    write_json(target, value)
                elif case == "summary":
                    value = read_json(target)
                    value["rows"] = 999
                    write_json(target, value)
                else:
                    write_json(target, [])
                before = target.read_bytes()
                with patch("audit_cmc_identity.requested_dates", return_value=["20210103"]):
                    with self.assertRaises(ValueError):
                        load_verified(args.source, args.lifecycle)
                self.assertEqual(before, target.read_bytes())

    def test_same_date_coverage_does_not_borrow_future_candidates(self):
        identities = [identity("BTC"), identity("LUNA"), identity("1000PEPE")]
        rows = [
            {"snapshot_date": "20210103", "symbol": "BTC", "vendor_asset_id": 1},
            {"snapshot_date": "20210103", "symbol": "PEPE", "vendor_asset_id": 2},
            {"snapshot_date": "20210110", "symbol": "LUNA", "vendor_asset_id": 3},
            {"snapshot_date": "20210110", "symbol": "LUNA", "vendor_asset_id": 4},
        ]
        weekly = coverage(identities, rows)
        first = weekly[0]["all_identifiers"]
        self.assertEqual(first["single_candidate"], 1)
        self.assertEqual(first["absent_unknown"], 2)
        self.assertEqual(weekly[1]["all_identifiers"]["multiple_candidates"], 1)
        self.assertEqual(
            sum(first[k] for k in ("single_candidate", "multiple_candidates", "absent_unknown")), 3
        )

    def test_rehashed_parsed_change_still_fails_independent_raw_parse(self):
        with tempfile.TemporaryDirectory() as directory:
            args = fixture(Path(directory))
            full = args.source / "full"
            target = full / "partitions/20210103.json"
            rows = read_json(target)
            rows[0]["market_cap_decimal"] = "999"
            write_json(target, rows)
            index = read_json(full / "index/20210103.json")
            index["parsed_sha256"] = digest(target.read_bytes())
            write_json(full / "index/20210103.json", index)
            write_json(full / "date_coverage.json", [index])
            with patch("audit_cmc_identity.requested_dates", return_value=["20210103"]):
                with self.assertRaisesRegex(ValueError, "raw/parsed content mismatch"):
                    load_verified(args.source, args.lifecycle)

    def test_known_reuse_and_single_match_remain_unapproved(self):
        identities = [identity("LIT")]
        identities[0]["known_identity_reuse"] = True
        rows = [
            {"snapshot_date": "20210103", "symbol": "LIT", "vendor_asset_id": 1, "name": "Litentry"}
        ]
        queue = review_queue(identities, rows, mapping_review(identities, rows))
        self.assertIn("known_contract_identity_reuse", queue[0]["review_flags"])
        self.assertIsNone(queue[0]["approved_mapping"])
        self.assertEqual(queue[0]["approved_episodes"], [])
        self.assertFalse(queue[0]["historical_strategy_eligible"])


if __name__ == "__main__":
    unittest.main()
