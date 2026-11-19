from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_early_identity_batch3 as batch  # noqa: E402
from acquire_usdm_universe import digest, read_json, write_json  # noqa: E402


def asset(symbol):
    return next(a for a in read_json(batch.CONFIG)["assets"] if a["symbol"] == symbol)


class IdentityBatch3Tests(unittest.TestCase):
    def test_alias_names_require_same_numeric_id(self):
        for symbol, name in (("BNB", "Binance Coin"), ("THETA", "Theta Token")):
            a = asset(symbol)
            current = {"id": a["vendor_asset_id"], "name": name, "symbol": symbol}
            self.assertTrue(batch.provider_labels_match(a, current))
            self.assertFalse(batch.provider_labels_match(a, {**current, "id": 999999}))

    def test_ven_and_tfuel_are_not_ticker_aliases(self):
        for symbol, wrong in (("VET", "VEN"), ("THETA", "TFUEL")):
            a = asset(symbol)
            self.assertIn(wrong, a["rejected_ticker_aliases"])
            self.assertFalse(
                batch.provider_labels_match(
                    a, {"id": a["vendor_asset_id"], "name": a["name"], "symbol": wrong}
                )
            )

    def test_bat_exact_ethereum_address_and_platform(self):
        expected = asset("BAT")["ethereum_contract"]
        right = {"contracts": [{"contractPlatform": "Ethereum", "contractAddress": expected}]}
        self.assertTrue(batch.identity.ethereum_contract(right, expected))
        self.assertFalse(
            batch.identity.ethereum_contract(
                {"contracts": [{"contractPlatform": "Solana", "contractAddress": expected}]},
                expected,
            )
        )
        self.assertFalse(batch.identity.ethereum_contract(right, expected[:-1] + "0"))

    def test_missing_completion_gate_blocks_identity_without_rescaling(self):
        a = asset("VET")
        decision = batch.constrained_rule(
            a, {"identity": True, "pre2020_swap_completed": False}, "2021-01-01T00:00:00+00:00"
        )
        self.assertFalse(decision["size_identity_join_allowed"])
        self.assertEqual(decision["usd_market_cap_scale"], "1")
        self.assertFalse(decision["price_or_history_splice_allowed"])

    def test_support_notice_does_not_prove_native_phase(self):
        decision = batch.constrained_rule(
            asset("IOST"),
            {"identity": True, "mainnet_support_acknowledged": True},
            "2021-01-01T00:00:00+00:00",
        )
        self.assertEqual(decision["migration_state"], "support_only_completion_unverified")
        self.assertFalse(decision["historical_native_phase_proven"])
        self.assertFalse(decision["full_contract_specifications_verified"])

    def test_qtum_identity_pass_does_not_repair_funding(self):
        a = asset("QTUM")
        before = copy.deepcopy(a)
        decision = batch.constrained_rule(
            a, {"identity": True, "launch": True}, "2021-01-01T00:00:00+00:00"
        )
        self.assertTrue(decision["size_identity_join_allowed"])
        self.assertFalse(decision["funding_cashflows_verified"])
        self.assertEqual(
            decision["known_early_funding_limitations"]["events_before_proposed_launch"], 2
        )
        decision["known_early_funding_limitations"]["cashflows_proven"] = True
        self.assertEqual(a, before)

    def test_fixed_sources_and_failure_replay(self):
        config = read_json(batch.CONFIG)
        self.assertEqual(len(batch.sources(config)), 26)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_json(
                root / "capture_summary.json",
                {"config_sha256": digest(batch.CONFIG.read_bytes()), "success": False},
            )
            with (
                patch.object(batch, "OUTPUT", root),
                patch.object(batch, "Downloader", side_effect=AssertionError("no HTTP")),
            ):
                summary, count = batch.capture(config, [])
                self.assertFalse(summary["success"])
                self.assertEqual(count, 0)
