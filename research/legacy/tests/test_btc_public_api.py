from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_btc_public_api as audit  # noqa: E402


def bars():
    api = [[0, "10", "12", "9", "11", "3", audit.HOUR - 1, "33", 4, "2", "22", "0"]]
    archive = [
        {
            "bar_open_ms": 0,
            "open_raw": "10.0",
            "high_raw": "12",
            "low_raw": "9",
            "close_raw": "11",
            "volume_raw": "3",
            "quote_volume_raw": "33",
            "trade_count": 4,
            "taker_buy_volume_raw": "2",
            "taker_buy_quote_volume_raw": "22",
        }
    ]
    return api, archive


class BtcPublicApiTests(unittest.TestCase):
    def test_fixed_plan_is_public_and_development_only(self):
        plan = json.loads(audit.CONFIG.read_text())
        self.assertEqual(len(plan["sources"]), 7)
        self.assertEqual(len(plan["partitions"]), 6)
        for source in plan["sources"]:
            url = urlsplit(source["url"])
            self.assertEqual(url.netloc, "fapi.binance.com")
            self.assertNotIn("signature", url.query)
            if "window" in source:
                w = next(w for w in plan["windows"] if w["id"] == source["window"])
                params = parse_qs(url.query)
                self.assertEqual(params["symbol"], ["BTCUSDT"])
                self.assertEqual(params["endTime"], [str(w["end_ms"] - 1)])
                self.assertTrue(w["start"].startswith("2020-"))

    def test_metadata_is_one_exact_usdt_perpetual_contract(self):
        row = {
            "symbol": "BTCUSDT",
            "pair": "BTCUSDT",
            "contractType": "PERPETUAL",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "marginAsset": "USDT",
            "onboardDate": 10,
        }
        self.assertTrue(audit.metadata_check({"symbols": [row]}, 20)["passed"])
        for key, value in [
            ("contractType", "CURRENT_QUARTER"),
            ("marginAsset", "BTC"),
            ("onboardDate", 30),
            ("onboardDate", True),
            ("baseAsset", "ETH"),
        ]:
            self.assertFalse(audit.metadata_check({"symbols": [{**row, key: value}]}, 20)["passed"])
        with self.assertRaisesRegex(ValueError, "one BTCUSDT"):
            audit.metadata_check({"symbols": [row, row]}, 20)

    def test_exact_decimal_comparison_and_no_mark_pseudo_volume_comparison(self):
        api, old = bars()
        self.assertTrue(audit.compare_bars(api, old, 0, audit.HOUR, "trade")["passed"])
        api[0][4] = "11.00000001"
        result = audit.compare_bars(api, old, 0, audit.HOUR, "trade")
        self.assertFalse(result["passed"])
        self.assertEqual(result["mismatch_count"], 1)
        api, old = bars()
        api[0][5], api[0][8] = "0", 0
        self.assertTrue(audit.compare_bars(api, old, 0, audit.HOUR, "mark")["passed"])
        self.assertFalse(audit.compare_bars(api, old, 0, audit.HOUR, "trade")["passed"])

    def test_bar_missing_duplicates_bad_clock_and_nonfinite_fail(self):
        api, old = bars()
        cases = [(api, old, 2 * audit.HOUR), (api + api, old, audit.HOUR)]
        bad = copy.deepcopy(api)
        bad[0][6] = audit.HOUR
        cases.append((bad, old, audit.HOUR))
        bad = copy.deepcopy(api)
        bad[0][4] = "NaN"
        cases.append((bad, old, audit.HOUR))
        for data, archive, end in cases:
            with self.assertRaises(ValueError):
                audit.compare_bars(data, archive, 0, end, "trade")

    def test_funding_requires_exact_timestamps_rates_and_nonempty_coverage(self):
        api = [{"symbol": "BTCUSDT", "fundingTime": 0, "fundingRate": "0.0001"}]
        old = [{"event_timestamp_ms": 0, "funding_rate_raw": "0.00010000"}]
        result = audit.compare_funding(api, old, 0, audit.HOUR)
        self.assertTrue(result["passed"])
        self.assertFalse(result["funding_payments_proven"])
        self.assertEqual(result["api_missing_reported_intervals"], 1)
        self.assertFalse(
            audit.compare_funding([{**api[0], "fundingTime": 1}], old, 0, audit.HOUR)["passed"]
        )
        self.assertFalse(
            audit.compare_funding([{**api[0], "fundingRate": "0.00010001"}], old, 0, audit.HOUR)[
                "passed"
            ]
        )
        for data in [[], api * 1000, api + api, [{**api[0], "symbol": "ETHUSDT"}]]:
            with self.assertRaises(ValueError):
                audit.compare_funding(data, old, 0, audit.HOUR)

    def test_non_json_success_response_is_not_evidence(self):
        self.assertFalse(
            audit.api_check(audit.metadata_check, b"<html>interstitial</html>", 20)["passed"]
        )

    def test_legacy_official_notice_body_is_supported(self):
        body = json.dumps(
            {
                "success": True,
                "data": {
                    "code": "360036964392",
                    "title": "Launch",
                    "body": "<p>Second perpetual contract ETH/USDT.</p><p>How to switch from BTC/USDT contract to ETH/USDT contract</p><p>2019/11/29</p>",
                },
            }
        ).encode()
        passed, report, _ = audit.article_check(
            body,
            "360036964392",
            [
                "second perpetual contract",
                "how to switch from btc/usdt contract to eth/usdt contract",
                "2019/11/29",
            ],
        )
        self.assertTrue(passed)
        self.assertEqual(report["body_format"], "legacy_html")

    def test_capture_failure_stops_other_requests_and_is_never_retried(self):
        plan = {
            "max_raw_bytes": 1024,
            "sources": [
                {"id": "info", "url": "https://fapi.binance.com/fapi/v1/exchangeInfo"},
                {"id": "bars", "url": "https://fapi.binance.com/fapi/v1/klines"},
            ],
        }
        first = Mock(requests=1)
        first.get.side_effect = ValueError("HTTP451 unavailable")
        second = Mock(requests=0)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(audit, "Downloader", return_value=first):
                _, outcomes, _ = audit.capture(plan, root, True)
            self.assertEqual(first.get.call_count, 1)
            self.assertEqual(outcomes["bars"]["state"], "not_requested")
            with patch.object(audit, "Downloader", return_value=second):
                _, replay, requests = audit.capture(plan, root, True)
            second.get.assert_not_called()
            self.assertEqual(requests, 0)
            self.assertEqual(outcomes, replay)
