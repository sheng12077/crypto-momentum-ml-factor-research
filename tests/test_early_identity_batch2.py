from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_early_identity_batch2 as batch  # noqa: E402
from acquire_usdm_universe import digest, read_json, write_json  # noqa: E402
from verify_early_size_identities import resolve_vendor  # noqa: E402


class IdentityBatch2Tests(unittest.TestCase):
    def test_selection_skips_prior_pending_not_just_passed(self):
        ranked = [{"instrument_id": s} for s in ("BTCUSDT", "IOTAUSDT", "TRXUSDT", "XLMUSDT")]
        old = [{"instrument_id": "BTCUSDT", "size_identity_join_allowed": False}]
        self.assertEqual(
            [r["instrument_id"] for r in batch.select_priority(ranked, old, ["IOTAUSDT"])],
            ["TRXUSDT", "XLMUSDT"],
        )

    def test_stellar_alias_does_not_override_id_or_symbol(self):
        asset = read_json(batch.CONFIG)["assets"][1]
        current = {"id": 512, "symbol": "XLM", "name": "Stellar Lumens"}
        self.assertTrue(batch.provider_labels_match(asset, current))
        for key, value in (("id", 999), ("symbol", "OTHER"), ("name", "Other Stellar")):
            bad = {**current, key: value}
            self.assertFalse(batch.provider_labels_match(asset, bad))

    def test_native_wrapped_addresses_not_identity_gate(self):
        asset = read_json(batch.CONFIG)["assets"][0]
        current = {
            "id": 1958,
            "name": "TRON",
            "symbol": "TRX",
            "contracts": [{"contractPlatform": "Unknown", "contractAddress": "wrapped"}],
        }
        self.assertTrue(batch.provider_labels_match(asset, current))
        self.assertTrue(asset["native_asset_expected"])
        rule = batch.rule(asset, {"venue_name": False}, "2021-01-01T00:00:00+00:00")
        self.assertFalse(rule["size_identity_join_allowed"])
        self.assertFalse(rule["onchain_identity_proven"])

    def test_new_rule_boundaries_and_old_rules_untouched(self):
        asset = read_json(batch.CONFIG)["assets"][0]
        before = copy.deepcopy(asset)
        rule = batch.rule(asset, {"all": True}, "2021-01-01T00:00:00+00:00")
        self.assertIsNone(
            resolve_vendor([rule], "TRXUSDT", datetime(2020, 1, 15, 7, 59, tzinfo=UTC))
        )
        self.assertEqual(
            resolve_vendor([rule], "TRXUSDT", datetime(2020, 1, 15, 8, tzinfo=UTC)), 1958
        )
        self.assertIsNone(resolve_vendor([rule], "TRXUSDT", datetime(2021, 1, 1, tzinfo=UTC)))
        self.assertEqual(asset, before)

    def test_fixed_source_budget_and_terminal_capture_replay(self):
        config = read_json(batch.CONFIG)
        self.assertEqual(len(batch.sources(config)), 24)
        bad = copy.deepcopy(config)
        bad["sources"].pop()
        with self.assertRaisesRegex(ValueError, "source count"):
            batch.sources(bad)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_json(
                root / "capture_summary.json",
                {"config_sha256": digest(batch.CONFIG.read_bytes()), "success": False},
            )
            with (
                patch.object(batch, "OUTPUT", root),
                patch.object(batch, "Downloader", side_effect=AssertionError("no network")),
            ):
                result, count = batch.capture(config, [])
                self.assertFalse(result["success"])
                self.assertEqual(count, 0)
