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
from collect_cmc_weekly import write_source  # noqa: E402
from review_contract_identity import (  # noqa: E402
    article_text,
    article_url,
    build,
    capture,
    validate_record,
)

CODE = "1" * 32
TEXT = "STRKUSDT Starknet 2024-02-20 17:00 UTC 1,000 SHIB"


def record():
    return {
        "instrument_id": "STRKUSDT",
        "assertions": [
            {
                "assertion_id": "launch",
                "event_type": "launch",
                "effective_at": "2024-02-20T17:00:00+00:00",
                "evidence": [{"article_code": CODE, "terms": ["Starknet", "2024-02-20 17:00"]}],
            }
        ],
        "proposed_episodes": [
            {
                "underlying": "Starknet",
                "proposed_vendor_asset_id": 22691,
                "effective_from": "2024-02-20T17:00:00+00:00",
                "effective_to": None,
                "start_assertion_id": "launch",
                "end_assertion_id": None,
                "assertion_ids": ["launch"],
                "underlying_tokens_per_price_unit": None,
                "unresolved": ["content_vintage", "end_boundary"],
            }
        ],
        "do_not_join_vendor_asset_ids": [8911],
    }


class ContractIdentityReviewTests(unittest.TestCase):
    def validate(self, item):
        return validate_record(item, {CODE: {"text": TEXT}}, {22691, 8911})

    def test_partial_identity_does_not_approve_join_or_availability(self):
        item = record()
        item["historical_join_approved"] = True
        result = self.validate(item)
        self.assertFalse(result["historical_join_approved"])
        self.assertFalse(result["point_in_time_ready"])
        self.assertIsNone(result["causal_available_at"])
        self.assertIsNone(result["proposed_episodes"][0]["effective_to"])

    def test_missing_evidence_or_wrong_terms_rejected(self):
        for mode in ("no_sources", "wrong_terms", "empty_assertions", "empty_episodes"):
            with self.subTest(mode=mode):
                item = record()
                if mode == "no_sources":
                    item["assertions"][0]["evidence"] = []
                elif mode == "wrong_terms":
                    item["assertions"][0]["evidence"][0]["terms"] = ["Strike"]
                elif mode == "empty_assertions":
                    item["assertions"] = []
                else:
                    item["proposed_episodes"] = []
                with self.assertRaises(ValueError):
                    self.validate(item)

    def test_rejected_or_uncaptured_vendor_cannot_be_proposed(self):
        for vendor in (8911, 9999999):
            item = record()
            item["proposed_episodes"][0]["proposed_vendor_asset_id"] = vendor
            with self.assertRaises(ValueError):
                self.validate(item)

    def test_utc_event_boundary_and_overlap_validation(self):
        for mode in ("naive", "wrong_time", "reversed", "overlap"):
            with self.subTest(mode=mode):
                item = record()
                episode = item["proposed_episodes"][0]
                if mode == "naive":
                    episode["effective_from"] = "2024-02-20T17:00:00"
                elif mode == "wrong_time":
                    episode["effective_from"] = "2024-02-21T17:00:00+00:00"
                elif mode == "reversed":
                    episode["effective_to"] = "2024-02-19T17:00:00+00:00"
                else:
                    item["proposed_episodes"].append(copy.deepcopy(episode))
                with self.assertRaises(ValueError):
                    self.validate(item)

    def test_units_require_matching_explicit_assertion(self):
        item = record()
        episode = item["proposed_episodes"][0]
        episode["underlying_tokens_per_price_unit"] = 1000
        with self.assertRaises(ValueError):
            self.validate(item)
        item["assertions"].append(
            {
                "assertion_id": "units",
                "underlying_tokens_per_price_unit": 1000,
                "evidence": [{"article_code": CODE, "terms": ["1,000 SHIB"]}],
            }
        )
        episode["assertion_ids"].append("units")
        episode["unit_assertion_id"] = "units"
        self.assertEqual(
            self.validate(item)["proposed_episodes"][0]["underlying_tokens_per_price_unit"], 1000
        )
        episode["underlying_tokens_per_price_unit"] = 1000000
        with self.assertRaises(ValueError):
            self.validate(item)

    def test_article_identity_and_source_budget(self):
        body = json.dumps({"success": True, "data": {"code": CODE, "body": "{}"}}).encode()
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            article_text(body, "2" * 32)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "budget"):
                capture({"sources": [CODE] * 61}, Path(directory))

    def test_offline_build_resume_and_raw_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, audit, config = root / "output", root / "audit", root / "config.json"
            body = json.dumps(
                {
                    "success": True,
                    "data": {
                        "code": CODE,
                        "title": "Official STRK launch",
                        "publishDate": 1708420000000,
                        "body": json.dumps(
                            {"node": "element", "child": [{"node": "text", "text": TEXT}]}
                        ),
                    },
                }
            ).encode()
            write_source(
                output,
                CODE,
                body,
                {
                    "status": 200,
                    "url": article_url(CODE),
                    "sha256": digest(body),
                    "bytes": len(body),
                },
            )
            write_json(config, {"sources": [CODE], "records": [record()]})
            write_json(audit / "summary.json", {"success": True})
            write_json(
                audit / "vendor_identity_history.json",
                [{"vendor_asset_id": 22691}, {"vendor_asset_id": 8911}],
            )
            write_json(
                audit / "identity_review_queue.json",
                [
                    {
                        "instrument_id": "STRKUSDT",
                        "candidate_ID_ambiguity": True,
                        "known_identity_reuse": False,
                        "review_flags": [],
                        "candidates_for_manual_review_only": [22691, 8911],
                    }
                ],
            )
            with (
                patch("review_contract_identity.AUDIT", audit),
                patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")),
                redirect_stdout(io.StringIO()),
            ):
                build(config, output)
                before = (output / "review_002/summary.json").read_bytes()
                build(config, output)
                self.assertEqual(before, (output / "review_002/summary.json").read_bytes())
                summary = read_json(output / "review_002/summary.json")
                self.assertEqual(summary["historical_joins_approved"], 0)
                self.assertTrue(summary["success"])
                (output / "raw" / (CODE + ".raw")).write_bytes(b"corrupt")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    build(config, output)


if __name__ == "__main__":
    unittest.main()
