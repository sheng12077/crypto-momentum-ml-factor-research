from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acquire_usdm_universe import digest, read_json, write_json  # noqa: E402
from build_identity_decisions import exclusion_reasons, validate_policy  # noqa: E402
from check_identity_followup import activity_stats, capture, parse_cmc_identity  # noqa: E402
from collect_cmc_weekly import write_source  # noqa: E402


class IdentityFollowupTests(unittest.TestCase):
    def setUp(self):
        self.policy = read_json(ROOT / "config/identity_decisions_20261118.json")
        self.population = {
            r["instrument_id"]
            for r in read_json(ROOT / "config/contract_identity_evidence_20261118.json")["records"]
        }

    def test_vendor_parser_excludes_price_performance_and_cap(self):
        detail = {
            "id": 10529,
            "name": "Sun New",
            "symbol": "SUN",
            "slug": "sun-token",
            "quote": {"price": 999, "percentChange": 99},
            "marketCap": 100,
            "platforms": [
                {
                    "contractAddress": "address",
                    "contractDecimals": 18,
                    "contractPlatform": "Tron",
                    "contractExplorerUrl": "https://example.test",
                }
            ],
        }
        payload = {"props": {"pageProps": {"detailRes": {"detail": detail}}}}
        body = ('<script id="__NEXT_DATA__">' + json.dumps(payload) + "</script>").encode()
        result = parse_cmc_identity(body)
        self.assertEqual(result["id"], 10529)
        self.assertNotIn("quote", result)
        self.assertNotIn("marketCap", result)
        self.assertFalse(result["historical_content_version_proven"])
        with self.assertRaises(ValueError):
            parse_cmc_identity(b"no structured identity")

    def test_activity_counts_do_not_treat_boundary_or_stubs_as_execution(self):
        rows = [
            [str(t), "1", "1", "1", "1", v] for t, v in ((0, "2"), (3600000, "1"), (7200000, "0"))
        ]
        result = activity_stats(rows, 3600000)
        self.assertEqual(result["positive_volume_rows"], 2)
        self.assertEqual(result["positive_volume_rows_at_or_after_close"], 1)
        self.assertEqual(result["distinct_price_strings"], 1)
        self.assertTrue(result["closure_boundary_bar_is_not_proven_executable"])
        with self.assertRaises(ValueError):
            activity_stats([rows[0], rows[0]], 3600000)

    def test_policy_covers_only_prior_priority_population(self):
        validate_policy(self.policy, self.population)
        self.assertEqual(len(self.population), 27)
        excluded = {r["instrument_id"] for r in self.policy["whole_identifier_exclusions"]}
        self.assertEqual(excluded, {"KNCUSDT", "DYDXUSDT", "MDTUSDT"})
        self.assertEqual(self.policy["historical_joins_approved"], 0)

    def test_negative_gate_scope_and_half_open_boundaries(self):
        at = "2025-01-01T00:00:00+00:00"
        self.assertTrue(exclusion_reasons(self.policy, "KNCUSDT", at, "size_join"))
        self.assertEqual(exclusion_reasons(self.policy, "KNCUSDT", at, "regular_execution"), [])
        self.assertEqual(
            exclusion_reasons(
                self.policy, "BNXUSDT", "2025-03-17T08:59:59+00:00", "regular_execution"
            ),
            [],
        )
        self.assertTrue(
            exclusion_reasons(
                self.policy, "BNXUSDT", "2025-03-17T09:00:00+00:00", "regular_execution"
            )
        )
        self.assertEqual(
            exclusion_reasons(self.policy, "BNXUSDT", "2023-02-11T04:00:00+00:00", "size_join"), []
        )
        self.assertTrue(
            exclusion_reasons(self.policy, "SUNUSDT", "2027-01-01T00:00:00+00:00", "size_join")
        )

    def test_rejected_vendor_cannot_be_retained(self):
        item = copy.deepcopy(self.policy)
        row = next(r for r in item["vendor_updates"] if r["instrument_id"] == "SUNUSDT")
        row["proposed_vendor_asset_id"] = 6990
        with self.assertRaisesRegex(ValueError, "contradiction"):
            validate_policy(item, self.population)

    def test_policy_rejects_unknown_ids_bad_utc_and_duplicates(self):
        for mode in ("unknown", "naive", "duplicate", "reverse"):
            with self.subTest(mode=mode):
                item = copy.deepcopy(self.policy)
                if mode == "unknown":
                    item["whole_identifier_exclusions"][0]["instrument_id"] = "UNKNOWN"
                elif mode == "naive":
                    item["interval_exclusions"][0]["from_utc"] = "2023-02-01T00:00:00"
                elif mode == "duplicate":
                    item["whole_identifier_exclusions"].append(
                        item["whole_identifier_exclusions"][0]
                    )
                else:
                    item["interval_exclusions"][0]["to_utc"] = "2021-01-01T00:00:00+00:00"
                with self.assertRaises(ValueError):
                    validate_policy(item, self.population)

    def test_no_implicit_sats_splice_or_cap_scaling(self):
        for key, value in (("automatic_cross_ID_splicing", True), ("cap_multiplier", 1000)):
            item = copy.deepcopy(self.policy)
            item["sats"][key] = value
            with self.assertRaises(ValueError):
                validate_policy(item, self.population)

    def test_forbidden_access_stops_remaining_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            write_json(
                config,
                {
                    "sources": [
                        {"id": "one", "url": "https://coinmarketcap.com/one/"},
                        {"id": "two", "url": "https://coinmarketcap.com/two/"},
                    ]
                },
            )
            with (
                patch("check_identity_followup.Downloader") as factory,
                redirect_stdout(io.StringIO()),
            ):
                factory.return_value.requests = 1
                factory.return_value.get.side_effect = ValueError("source access stopped HTTP 403")
                capture(config, root / "output")
                self.assertEqual(factory.return_value.get.call_count, 1)
            self.assertFalse(read_json(root / "output/capture_summary.json")["success"])

    def test_cached_not_found_is_not_requested_again_and_is_hash_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            url = "https://coinmarketcap.com/deleted/"
            config = root / "config.json"
            write_json(config, {"sources": [{"id": "deleted", "url": url}]})
            body = b"not found"
            write_source(
                root,
                "attempts/deleted/1",
                body,
                {"url": url, "status": 404, "sha256": digest(body), "bytes": len(body)},
            )
            with (
                patch("check_identity_followup.Downloader") as factory,
                redirect_stdout(io.StringIO()),
            ):
                factory.return_value.requests = 0
                capture(config, root)
                factory.return_value.get.assert_not_called()
                (root / "raw/attempts/deleted/1.raw").write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    capture(config, root)


if __name__ == "__main__":
    unittest.main()
