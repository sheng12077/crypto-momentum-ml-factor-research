from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import followup_early_identities as follow  # noqa: E402
from acquire_usdm_universe import digest, write_json  # noqa: E402
from verify_early_size_identities import decisions, resolve_vendor  # noqa: E402


def proofs():
    return dict.fromkeys(
        (
            "iota_historical_provider",
            "iota_units",
            "iota_origin",
            "uni_historical_provider_contract_origin",
            "uni_spot",
            "venue_month",
            "uni_futures",
        ),
        True,
    )


class FollowupTests(unittest.TestCase):
    def test_legacy_html_body_and_wrong_id(self):
        payload = {
            "success": True,
            "data": {
                "code": "115002193731",
                "title": "IOTA Trading Bounty",
                "body": "<p>The IOTA trading pair on Binance <b>1IOTA=1 MIOTA</b></p>",
            },
        }
        passed, report, content = follow.article_check(
            json.dumps(payload).encode(), "115002193731", ["1IOTA=1 MIOTA"]
        )
        self.assertTrue(passed)
        self.assertEqual(report["body_format"], "legacy_html")
        self.assertTrue(follow.prior.iota_unit_clause(content.encode()))
        with self.assertRaisesRegex(ValueError, "identity"):
            follow.article_check(json.dumps(payload).encode(), "wrong", [])

    def test_related_article_cannot_supply_missing_clause(self):
        payload = {
            "success": True,
            "data": {
                "code": "115002193731",
                "title": "IOTA Trading Bounty",
                "body": "<p>No unit clause here</p>",
                "relatedArticles": [{"body": "1IOTA=1 MIOTA"}],
            },
        }
        passed, _, _ = follow.article_check(
            json.dumps(payload).encode(), "115002193731", ["1IOTA=1 MIOTA"]
        )
        self.assertFalse(passed)

    def test_missing_evidence_does_not_approve_case(self):
        for key in proofs():
            proof = proofs()
            proof[key] = False
            rows = follow.supplemented_rules(decisions({}), proof)
            index = 0 if key.startswith("iota") else 1
            self.assertFalse(rows[index]["size_identity_join_allowed"])

    def test_launch_boundary_and_original_invariants(self):
        previous = decisions({})
        rows = follow.supplemented_rules(previous, proofs())
        self.assertEqual(rows[2:], previous[2:])
        self.assertFalse(previous[1]["size_identity_join_allowed"])
        self.assertIsNone(resolve_vendor(rows, "UNIUSDT", datetime(2020, 9, 18, 6, 59, tzinfo=UTC)))
        self.assertEqual(
            resolve_vendor(rows, "UNIUSDT", datetime(2020, 9, 18, 7, tzinfo=UTC)), 7083
        )
        self.assertIsNone(resolve_vendor(rows, "UNIUSDT", datetime(2021, 1, 1, tzinfo=UTC)))
        for row in rows:
            self.assertEqual(row["usd_market_cap_scale"], "1")
            self.assertFalse(row["price_or_history_splice_allowed"])
            self.assertFalse(row["historical_strategy_eligible"])

    def test_article_identity_and_spot_cannot_establish_futures(self):
        payload = {
            "success": True,
            "data": {
                "code": "wrong",
                "title": "UNI",
                "body": json.dumps({"node": "text", "text": "UNI/USDT"}),
            },
        }
        with self.assertRaisesRegex(ValueError, "identity"):
            follow.article_check(json.dumps(payload).encode(), follow.UNI_CODE, [])
        payload["data"]["code"] = follow.UNI_CODE
        passed, _, _ = follow.article_check(
            json.dumps(payload).encode(), follow.UNI_CODE, ["UNI/USDT perpetual contract"]
        )
        self.assertFalse(passed)

    def test_monthly_link_requires_exact_article_and_pair(self):
        body = (
            'Uniswap USDT-margined perpetual contracts <a href="https://www.binance.com/en/support/announcement/'
            + follow.UNI_CODE
            + '">UNI/USDT</a>'
        )
        self.assertTrue(follow.monthly_link(body.encode()))
        self.assertFalse(follow.monthly_link(body.replace(follow.UNI_CODE, "wrong").encode()))
        self.assertFalse(follow.monthly_link(body.replace("UNI/USDT</a>", "UNI/BTC</a>").encode()))

    def test_terminal_failure_is_frozen_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_json(
                root / "capture_summary.json",
                {"config_sha256": digest(follow.CONFIG.read_bytes()), "success": False},
            )
            with (
                patch.object(follow, "OUTPUT", root),
                patch.object(follow, "Downloader", side_effect=AssertionError("no HTTP")),
            ):
                report, requests = follow.capture_once({})
                self.assertFalse(report["success"])
                self.assertEqual(requests, 0)
                target = root / "raw/attempts/test/1.json"
                write_json(target, {"sha256": digest(b"original"), "bytes": 8})
                target.with_suffix(".raw").write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    follow.capture_once({})
