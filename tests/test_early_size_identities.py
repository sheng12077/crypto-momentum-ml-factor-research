from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_early_size_identities import (  # noqa: E402
    decisions,
    ethereum_contract,
    iota_unit_clause,
    provider,
    resolve_vendor,
)


def proof():
    return {
        key: True
        for key in (
            "iota_provider",
            "iota_history",
            "iota_project",
            "iota_units",
            "uni_provider",
            "uni_contract",
            "uni_origin",
            "uni_project",
            "uni_history",
            "aave_provider",
            "aave_contract",
            "aave_origin",
            "migration_notice",
            "aave_lend_history",
        )
    }


class EarlyIdentityTests(unittest.TestCase):
    def test_redirected_numeric_id_rejected(self):
        payload = {
            "props": {
                "pageProps": {
                    "detailRes": {
                        "detail": {
                            "id": 7278,
                            "name": "Aave",
                            "symbol": "AAVE",
                            "slug": "aave",
                            "platforms": [],
                        }
                    }
                }
            }
        }
        body = ('<script id="__NEXT_DATA__">' + json.dumps(payload) + "</script>").encode()
        self.assertEqual(provider(body, 7278)["id"], 7278)
        with self.assertRaisesRegex(ValueError, "ID mismatch"):
            provider(body, 2239)

    def test_contract_chain_and_full_address_must_match(self):
        identity = {"contracts": [{"contractPlatform": "Ethereum", "contractAddress": "0xABC"}]}
        self.assertTrue(ethereum_contract(identity, "0xabc"))
        self.assertFalse(ethereum_contract(identity, "0xdef"))
        identity["contracts"][0]["contractPlatform"] = "Polygon"
        self.assertFalse(ethereum_contract(identity, "0xabc"))

    def test_unit_clause_not_a_million_times_cap(self):
        self.assertTrue(iota_unit_clause(b"<p>1IOTA = 1 MIOTA</p>"))
        self.assertFalse(iota_unit_clause(b"1 MIOTA = 1000000 micro IOTA"))
        rules = decisions(proof())
        self.assertTrue(rules[0]["size_identity_join_allowed"])
        self.assertEqual(rules[0]["usd_market_cap_scale"], "1")

    def test_missing_source_blocks_alias(self):
        evidence = proof()
        evidence["iota_units"] = False
        self.assertFalse(decisions(evidence)[0]["size_identity_join_allowed"])

    def test_lend_aave_bounds_and_no_shared_url_splice(self):
        rules = decisions(proof())
        self.assertEqual(resolve_vendor(rules, "LENDUSDT", datetime(2020, 10, 9, tzinfo=UTC)), 2239)
        self.assertIsNone(resolve_vendor(rules, "LENDUSDT", datetime(2020, 10, 10, tzinfo=UTC)))
        self.assertIsNone(resolve_vendor(rules, "AAVEUSDT", datetime(2020, 10, 16, 6, tzinfo=UTC)))
        self.assertEqual(
            resolve_vendor(rules, "AAVEUSDT", datetime(2020, 10, 16, 7, tzinfo=UTC)), 7278
        )
        self.assertIsNone(resolve_vendor(rules, "AAVEUSDT", datetime(2021, 1, 1, tzinfo=UTC)))

    def test_uni_asset_identity_does_not_prove_futures_listing(self):
        rules = decisions(proof())
        self.assertTrue(rules[1]["asset_identity_supported"])
        self.assertFalse(rules[1]["size_identity_join_allowed"])
        self.assertEqual(rules[1]["rejected_vendor_ids"], [4113])
        self.assertIsNone(resolve_vendor(rules, "UNIUSDT", datetime(2020, 12, 1, tzinfo=UTC)))

    def test_rescale_and_history_splice_forbidden(self):
        for field, value in (
            ("usd_market_cap_scale", "1000000"),
            ("price_or_history_splice_allowed", True),
        ):
            rules = copy.deepcopy(decisions(proof()))
            rules[0][field] = value
            with self.assertRaisesRegex(ValueError, "rescale"):
                resolve_vendor(rules, "IOTAUSDT", datetime(2020, 6, 1, tzinfo=UTC))
