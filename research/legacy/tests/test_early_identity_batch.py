from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_early_identity_batch as batch  # noqa: E402
from acquire_usdm_universe import digest, read_json, write_json  # noqa: E402


def asset():
    return read_json(batch.CONFIG)["assets"][0]


def row(**extra):
    return {
        "vendor_asset_id": 1831,
        "name": "Bitcoin Cash",
        "symbol": "BCH",
        "snapshot_date": "20200503",
        **extra,
    }


class IdentityBatchTests(unittest.TestCase):
    def test_inline_parenthesis_spacing_but_not_title_fallback(self):
        spec = {"source": {"article_code": "right"}}
        payload = {
            "success": True,
            "data": {
                "code": "right",
                "title": "Ethereum Classic (ETC)",
                "body": "<p>About ChainLink ( <a>LINK</a> )</p>",
            },
        }
        source = {"source": (json.dumps(payload).encode(),)}
        self.assertTrue(batch.source_terms("source", ["ChainLink (LINK)"], source, spec)[0])
        self.assertFalse(batch.source_terms("source", ["Ethereum Classic (ETC)"], source, spec)[0])

    def test_historical_numeric_id_and_name_required(self):
        self.assertTrue(batch.historical_check(asset(), [row()])[0])
        for records in (
            [],
            [row(vendor_asset_id=1)],
            [row(name="Other Cash")],
            [row(symbol="BCHA")],
        ):
            self.assertFalse(batch.historical_check(asset(), records)[0])

    def test_collision_scoped_by_historical_date(self):
        a = asset()
        ok, _ = batch.historical_check(a, [row(), row(vendor_asset_id=999)])
        self.assertFalse(ok)
        # A later asset using a symbol does not retroactively exclude this interval.
        ok, _ = batch.historical_check(
            a, [row(), row(vendor_asset_id=999, snapshot_date="20210503")]
        )
        self.assertTrue(ok)

    def test_each_missing_gate_blocks_join_and_keeps_limits(self):
        proof = dict.fromkeys(
            (
                "historical_identity",
                "provider_identity",
                "venue_name",
                "venue_futures",
                "token_contract",
            ),
            True,
        )
        for key in proof:
            missing = copy.copy(proof)
            missing[key] = False
            result = batch.rule(asset(), missing, "2021-01-01T00:00:00+00:00")
            self.assertFalse(result["size_identity_join_allowed"])
            self.assertIn(key, result["pending_gates"])
            self.assertFalse(result["historical_strategy_eligible"])
            self.assertEqual(result["usd_market_cap_scale"], "1")
            self.assertFalse(result["price_or_history_splice_allowed"])

    def test_bch_fork_boundary_is_exclusive(self):
        rule = batch.rule(asset(), {"passed": True}, "2021-01-01T00:00:00+00:00")
        self.assertEqual(
            batch.identity.resolve_vendor(
                [rule], "BCHUSDT", datetime(2020, 11, 15, 11, 59, tzinfo=UTC)
            ),
            1831,
        )
        self.assertIsNone(
            batch.identity.resolve_vendor([rule], "BCHUSDT", datetime(2020, 11, 15, 12, tzinfo=UTC))
        )

    def test_exact_cms_article_and_its_body_only(self):
        spec = {"source": {"article_code": "right"}}
        payload = {
            "success": True,
            "data": {"code": "wrong", "title": "Bitcoin", "body": "<p>Bitcoin (BTC)</p>"},
        }
        self.assertFalse(
            batch.source_terms(
                "source", ["Bitcoin"], {"source": (json.dumps(payload).encode(),)}, spec
            )[0]
        )
        payload["data"]["code"] = "right"
        self.assertTrue(
            batch.source_terms(
                "source", ["Bitcoin (BTC)"], {"source": (json.dumps(payload).encode(),)}, spec
            )[0]
        )
        self.assertFalse(batch.source_terms("source", ["Bitcoin"], {}, spec)[0])

    def test_failed_capture_not_retried_and_corruption_rejected(self):
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
                report, count = batch.capture({}, [])
                self.assertFalse(report["success"])
                self.assertEqual(count, 0)
                path = root / "raw/attempts/test/1.json"
                write_json(path, {"sha256": digest(b"original"), "bytes": 8})
                path.with_suffix(".raw").write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    batch.capture({}, [])
