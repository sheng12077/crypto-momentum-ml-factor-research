import io
import json
import sys
import tempfile
import unittest
import urllib.error
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acquire_usdm_universe import digest, read_json, write_json  # noqa: E402
from collect_cmc_weekly import (  # noqa: E402
    CalendarLinks,
    Downloader,
    checked_source,
    mapping_review,
    raw_bytes,
    requested_dates,
    run,
    write_source,
)


class Response(io.BytesIO):
    code = 200
    headers = {}


class CMCWeeklyTest(unittest.TestCase):
    def test_frozen_calendar_has_carry_and_no_future_dates(self):
        dates = requested_dates()
        self.assertEqual(len(dates), 305)
        self.assertEqual(dates[0], "20201227")
        self.assertEqual(dates[1], "20210103")
        self.assertEqual(dates[-1], "20261025")
        self.assertEqual(len(set(dates)), len(dates))

    def test_calendar_uses_public_same_origin_links_only(self):
        parser = CalendarLinks()
        parser.feed(
            '<a href="/historical/20210103/">ok</a><a href="https://evil.test/historical/20210110/">no</a><a href="/historical/20210103/">duplicate</a>'
        )
        self.assertEqual(parser.dates, {"20210103"})

    def test_cached_raw_is_checked_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root, body, url = Path(directory), b"checked", "https://example.test"
            report = {"status": 200, "url": url, "bytes": len(body), "sha256": digest(body)}
            write_source(root, "20210103", body, report)
            with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
                _, _, cached = Downloader(root, 100).get("20210103", url)
                self.assertTrue(cached)
                (root / "raw/20210103.raw").write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    checked_source(root, "20210103", url)

    def test_forbidden_status_stops_after_one_request(self):
        url = "https://example.test/forbidden"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            error = urllib.error.HTTPError(url, 403, "forbidden", {}, io.BytesIO(b"blocked"))
            with patch("urllib.request.urlopen", side_effect=error) as request, patch("time.sleep"):
                with self.assertRaisesRegex(ValueError, "stopped all acquisition"):
                    Downloader(root, 100).get("20210103", url)
                self.assertEqual(request.call_count, 1)
                self.assertTrue((root / "access_pause.json").exists())
                self.assertLessEqual(raw_bytes(root), 100)

    def test_transient_failures_retry_at_most_three_times(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch(
                    "urllib.request.urlopen", side_effect=urllib.error.URLError("reset")
                ) as request,
                patch("time.sleep"),
            ):
                with self.assertRaisesRegex(ValueError, "three attempts"):
                    Downloader(Path(directory), 100).get("20210103", "https://example.test")
                self.assertEqual(request.call_count, 3)

    def test_transient_failure_then_success_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch(
                    "urllib.request.urlopen",
                    side_effect=[urllib.error.URLError("reset"), Response(b"okay")],
                ),
                patch("time.sleep"),
            ):
                body, report, cached = Downloader(root, 100).get("20210103", "https://example.test")
            self.assertEqual(body, b"okay")
            self.assertEqual(report["attempt"], 2)
            self.assertFalse(cached)
            self.assertEqual(len(list((root / "raw/attempts").rglob("*.json"))), 1)

    def test_response_cannot_exceed_byte_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("urllib.request.urlopen", return_value=Response(b"123456789")),
                patch("time.sleep"),
            ):
                with self.assertRaisesRegex(ValueError, "bounded"):
                    Downloader(root, 4).get("20210103", "https://example.test")
            self.assertEqual(raw_bytes(root), 4)
            self.assertFalse((root / "raw/20210103.json").exists())

    def test_reuse_candidates_are_not_approved_or_merged(self):
        identities = [
            {
                "instrument_id": "LITUSDT",
                "known_identity_reuse": True,
                "current_product_metadata": {"baseAsset": "LIT"},
            }
        ]
        rows = [
            {
                "symbol": "LIT",
                "vendor_asset_id": 1,
                "name": "Litentry",
                "snapshot_date": "20210103",
            },
            {"symbol": "LIT", "vendor_asset_id": 2, "name": "Lighter", "snapshot_date": "20261025"},
        ]
        result = mapping_review(identities, rows)[0]
        self.assertEqual(len(result["candidates_for_manual_review_only"]), 2)
        self.assertTrue(result["candidate_ID_ambiguity"])
        self.assertIsNone(result["approved_mapping"])
        self.assertFalse(result["historical_strategy_eligible"])

    def test_full_mode_resume_and_parsed_corruption_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_dir = root / "lifecycle"
            identities = [
                {
                    "instrument_id": "BTCUSDT",
                    "known_identity_reuse": False,
                    "current_product_metadata": {"baseAsset": "BTC"},
                }
            ]
            write_json(ledger_dir / "identity_ledger.json", identities)
            write_json(
                ledger_dir / "summary.json",
                {
                    "success": True,
                    "ledger_sha256": digest((ledger_dir / "identity_ledger.json").read_bytes()),
                },
            )
            plan = {"requested_dates": ["20210103"], "listed_requested_dates": ["20210103"]}
            write_json(root / "plan.json", plan)
            row = {
                "id": 1,
                "name": "Bitcoin",
                "symbol": "BTC",
                "slug": "bitcoin",
                "circulatingSupply": "18000000",
                "quote": {
                    "USD": {
                        "marketCap": "500000000001.000001",
                        "lastUpdated": "2021-01-03T23:00:00Z",
                    }
                },
            }
            state = {"cryptocurrency": {"listingHistorical": {"data": [row]}}}
            payload = {"props": {"initialState": json.dumps(state)}}
            body = (
                "<title>Historical Snapshot - 03 January 2021</title>"
                + '<script id="__NEXT_DATA__">'
                + json.dumps(payload)
                + "</script>"
            ).encode()
            url = "https://coinmarketcap.com/historical/20210103/"
            write_source(
                root,
                "20210103",
                body,
                {"status": 200, "url": url, "bytes": len(body), "sha256": digest(body)},
            )
            args = Namespace(
                action="download", output_root=root, lifecycle_dir=ledger_dir, max_mib=256
            )
            with (
                patch("collect_cmc_weekly.make_plan", return_value=plan),
                patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")),
                redirect_stdout(io.StringIO()),
            ):
                self.assertTrue(run(args))
                self.assertTrue(run(args))
                summary = read_json(root / "full/summary.json")
                self.assertTrue(summary["full_scope"])
                self.assertEqual(summary["verified_dates"], 1)
                self.assertEqual(summary["http_requests"], 0)
                self.assertFalse(summary["historical_eligible_universe_ready"])
                (root / "full/partitions/20210103.json").write_text("[]")
                self.assertFalse(run(args))
                self.assertIn(
                    "integrity", read_json(root / "full/summary.json")["errors"][0]["error"]
                )

    def test_scaled_prefix_is_not_silently_stripped(self):
        identities = [
            {
                "instrument_id": "1000PEPEUSDT",
                "known_identity_reuse": False,
                "current_product_metadata": {"baseAsset": "1000PEPE"},
            }
        ]
        rows = [
            {"symbol": "PEPE", "vendor_asset_id": 1, "name": "Pepe", "snapshot_date": "20261025"}
        ]
        self.assertEqual(
            mapping_review(identities, rows)[0]["candidates_for_manual_review_only"], []
        )


if __name__ == "__main__":
    unittest.main()
