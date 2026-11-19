from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_early_cases as cases  # noqa: E402
from acquire_usdm_universe import digest, write_json  # noqa: E402
from check_early_cases import END, START, overlap_check, parse_funding, verified_article  # noqa: E402


def event(stamp=START, rate="0.00010000", **extra):
    return {
        "symbol": "QTUMUSDT",
        "fundingTime": stamp,
        "fundingRate": rate,
        "markPrice": "",
        **extra,
    }


class EarlyCasesTests(unittest.TestCase):
    def test_terminal_capture_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_json(
                root / "capture_summary.json",
                {
                    "config_sha256": digest(cases.CONFIG.read_bytes()),
                    "success": False,
                    "http_requests": 4,
                },
            )
            with (
                patch.object(cases, "OUTPUT", root),
                patch.object(cases, "capture", side_effect=AssertionError("must not retry")),
            ):
                summary, reused = cases.capture_once()
                self.assertTrue(reused)
                self.assertFalse(summary["success"])

    def test_terminal_failure_raw_integrity_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_json(
                root / "capture_summary.json", {"config_sha256": digest(cases.CONFIG.read_bytes())}
            )
            target = root / "raw/attempts/qtum_launch/1.json"
            write_json(target, {"sha256": digest(b"original"), "bytes": 8})
            target.with_suffix(".raw").write_bytes(b"changed")
            with (
                patch.object(cases, "OUTPUT", root),
                self.assertRaisesRegex(ValueError, "integrity"),
            ):
                cases.capture_once()

    def test_raw_precision_missing_price_and_unknown_interval_preserved(self):
        row = parse_funding([event()])[0]
        self.assertEqual(row["funding_rate_raw"], "0.00010000")
        self.assertEqual(row["mark_price_raw"], "")
        self.assertIsNone(row["reported_funding_interval_hours"])
        self.assertIsNone(row["available_at"])
        self.assertFalse(row["funding_payment_proven"])

    def test_bad_identity_bounds_order_and_duplicates_fail(self):
        for payload in (
            [event(START - 1)],
            [event(END + 1)],
            [event(symbol="BTCUSDT")],
            [event(), event()],
            [event(START + 1), event(START)],
        ):
            with self.assertRaises(ValueError):
                parse_funding(payload)

    def test_invalid_values_and_saturated_page_fail(self):
        for row in (event(rate="NaN"), event(markPrice="0"), event(fundingIntervalHours=0)):
            with self.assertRaises(ValueError):
                parse_funding([row])
        with self.assertRaisesRegex(ValueError, "saturated"):
            parse_funding([event()] * 1000)

    def test_exact_decimal_overlap_and_mismatch(self):
        rows = parse_funding([event(END)])
        self.assertTrue(
            overlap_check(rows, [{"event_ms": END, "rate_raw": "0.0001"}])["rate_matches"]
        )
        self.assertFalse(
            overlap_check(rows, [{"event_ms": END, "rate_raw": "0.0002"}])["rate_matches"]
        )
        self.assertFalse(
            overlap_check([], [{"event_ms": END, "rate_raw": "0.0001"}])["rate_matches"]
        )

    def test_article_code_and_missing_clauses_fail(self):
        code = "a" * 32
        body = json.dumps(
            {
                "success": True,
                "data": {
                    "code": code,
                    "title": "Source title",
                    "body": json.dumps(
                        {
                            "node": "root",
                            "child": [{"node": "text", "text": "Launch 2020/08/28 7:00 AM (UTC)."}],
                        }
                    ),
                },
            }
        ).encode()
        verified, _ = verified_article(body, code, ["2020/08/28 7:00 AM (UTC)"])
        self.assertTrue(verified["clauses_verified"])
        missing, _ = verified_article(body, code, ["not the ticker of a separate token"])
        self.assertFalse(missing["clauses_verified"])
        self.assertFalse(verified["historical_content_version_proven"])
        with self.assertRaisesRegex(ValueError, "identity"):
            verified_article(body, "b" * 32, [])
