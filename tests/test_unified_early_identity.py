from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_early_identity as unified  # noqa: E402
from acquire_usdm_universe import digest, write_json  # noqa: E402


def item(symbol="BTCUSDT", weeks=10):
    return {
        "instrument_id": symbol,
        "price_history_candidate_weeks": weeks,
        "literal_IDs_change_or_multiple": False,
        "literal_vendor_proposals": {"1": ["20200105"]},
    }


class UnifiedIdentityTests(unittest.TestCase):
    def test_unfinished_template_cannot_pass_with_empty_terms(self):
        asset = {
            "provider": "s",
            "name_source": "s",
            "future_source": "s",
            "name_terms": [],
            "future_terms": [],
            "native_asset_expected": True,
            "scope_from": "2020-01-01T00:00:00+00:00",
        }
        plan = {"sources": [{"id": "s", "url": "https://www.binance.com/test"}], "assets": [asset]}
        with self.assertRaisesRegex(ValueError, "nonempty"):
            unified.validate_extra_plan(plan)
        asset.update(name_terms=["Token (TOK)"], future_terms=["TOK/USDT perpetual contract"])
        unified.validate_extra_plan(plan)
        asset["scope_from"] = "2020-01-01T00:00:00"
        with self.assertRaisesRegex(ValueError, "review window"):
            unified.validate_extra_plan(plan)

    def test_report_hash_tampering_and_portable_attempt_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / "raw/attempts/test/1.json"
            write_json(p, {"sha256": digest(b"failure"), "bytes": 7})
            p.with_suffix(".raw").write_bytes(b"failure")
            self.assertIn("raw/attempts/test/1.json", unified.verify_attempts(root))
            output = root / "asset_review.json"
            output.write_bytes(b"original")
            summary = {"output_hashes": {"asset_review.json": digest(b"original")}}
            unified.verify_output_hashes(root, summary)
            output.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "report integrity"):
                unified.verify_output_hashes(root, summary)

    def test_unique_ticker_lead_is_not_approval(self):
        result = unified.row_status(item(), None)
        self.assertEqual(result["identity_status"], "needs_source_assertions")
        self.assertIn("official_name_source", result["missing_requirements"])
        self.assertFalse(result["strict_strategy_eligible"])

    def test_identity_and_history_are_independent(self):
        result = unified.row_status(
            item("AAVEUSDT", 0), {"mapping": {"size_identity_join_allowed": True}}
        )
        self.assertEqual(result["identity_status"], "corroborated_identity")
        self.assertEqual(result["price_history_state"], "no_candidate_week")
        self.assertFalse(result["strict_strategy_eligible"])

    def test_index_retained_but_not_single_token(self):
        result = unified.row_status(item("DEFIUSDT", 0), None)
        self.assertEqual(result["identity_status"], "composite_index")
        self.assertEqual(result["instrument_id"], "DEFIUSDT")

    def test_duplicate_needs_exact_explicit_replacement(self):
        registry = {}
        old = {"instrument_id": "BTCUSDT", "size_identity_join_allowed": False}
        new = {**old, "size_identity_join_allowed": True}
        unified.register_rule(registry, old, "old")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            unified.register_rule(registry, new, "new")
        unified.register_rule(
            registry,
            new,
            "new",
            {
                "replaces_rule_sha256": unified.fingerprint(old),
                "replacement_reason": "new registered primary evidence",
            },
        )
        self.assertEqual(registry["BTCUSDT"]["superseded"]["mapping"], old)

    def test_additional_url_deduplication(self):
        url = "https://www.binance.com/example"
        meta = {"url": url, "status": 200, "sha256": digest(b"ok"), "bytes": 2}
        downloader = Mock(requests=1)
        downloader.get.return_value = (b"ok", meta, False)
        plan = {
            "max_raw_bytes": 1024,
            "sources": [{"id": "one", "url": url}, {"id": "two", "url": url}],
        }
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(unified, "Downloader", return_value=downloader),
        ):
            found, _, outcomes, _ = unified.additional_sources(plan, Path(folder), True, {}, set())
            self.assertEqual(len(found), 2)
            self.assertEqual(downloader.get.call_count, 1)
            self.assertEqual(outcomes["one"], outcomes["two"])

    def test_old_failed_url_not_retried(self):
        url = "https://www.binance.com/frozen"
        downloader = Mock(requests=0)
        downloader.get.side_effect = AssertionError("must not retry")
        plan = {"max_raw_bytes": 1024, "sources": [{"id": "old", "url": url}]}
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(unified, "Downloader", return_value=downloader),
        ):
            found, _, outcomes, requests = unified.additional_sources(
                plan, Path(folder), True, {}, {url}
            )
            self.assertFalse(found)
            self.assertEqual(requests, 0)
            self.assertEqual(outcomes["old"]["reason"], "frozen_prior_failure")

    def test_terminal_checkpoint_integrity_and_no_network(self):
        url = "https://www.binance.com/failure"
        key = digest(url.encode())
        downloader = Mock(requests=0)
        downloader.get.side_effect = AssertionError("no HTTP")
        plan = {"max_raw_bytes": 1024, "sources": [{"id": "bad", "url": url}]}
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(unified, "Downloader", return_value=downloader),
        ):
            output = Path(folder)
            root = output / "additional_cache"
            path = root / "raw/attempts" / key / "1.json"
            write_json(path, {"sha256": digest(b"error"), "bytes": 5})
            path.with_suffix(".raw").write_bytes(b"error")
            write_json(
                root / "terminal" / (key + ".json"),
                {"url": url, "error": "HTTP202", "attempt_hashes": unified.verify_attempts(root)},
            )
            found, _, outcomes, count = unified.additional_sources(plan, output, True, {}, set())
            self.assertFalse(found)
            self.assertEqual(count, 0)
            self.assertEqual(outcomes["bad"]["state"], "terminal_failure")
            path.with_suffix(".raw").write_bytes(b"tamper")
            with self.assertRaisesRegex(ValueError, "integrity"):
                unified.additional_sources(plan, output, True, {}, set())

    def test_config_tampering_rejected_before_using_review(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(unified, "ROOT", Path(folder)):
            root = Path(folder)
            write_json(root / "config.json", {"sources": []})
            write_json(
                root / "cache/review/run_config.json", {"config_sha256": digest(b"different")}
            )
            with self.assertRaisesRegex(ValueError, "configuration changed"):
                unified.load_review(
                    {
                        "config": "config.json",
                        "root": "cache",
                        "review": "review",
                        "tool": "unused.py",
                    },
                    {},
                    {},
                )

    def test_no_eight_source_limit_or_unsafe_labels(self):
        plan = {
            "sources": [
                {"id": f"case{i}", "url": "https://www.binance.com/" + str(i)} for i in range(81)
            ]
        }
        self.assertEqual(len(unified.source_specs(plan)), 81)
        plan["sources"].append({"id": "../unsafe", "url": "https://www.binance.com/"})
        with self.assertRaisesRegex(ValueError, "unsafe"):
            unified.source_specs(plan)
