import importlib.util
import json
import sys
import tempfile
import unittest
import urllib.parse
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from recover_mark_gaps import (  # noqa: E402
    HOUR,
    RateGate,
    SourceConflict,
    context_flags,
    digest,
    export_overlay,
    recover_job,
    validate_response,
    verified_seeds,
)

START = 1609459200000


def job():
    prices = {"open": "100", "high": "110", "low": "90", "close": "105"}
    return {
        "job_id": "a" * 64,
        "symbol": "TESTUSDT",
        "prior_ms": START,
        "next_ms": START + 3 * HOUR,
        "targets": [START + HOUR, START + 2 * HOUR],
        "boundaries": {str(START): prices, str(START + 3 * HOUR): prices},
        "current_metadata": {"underlyingType": "COIN"},
        "last_positive_trade_bar": "2021-01-01T00:00:00+00:00",
        "lifecycle_events": [{"effective_at": "2021-01-01T01:00:00+00:00"}],
    }


def payload():
    return [
        [
            START + i * HOUR,
            "100",
            "110",
            "90",
            "105",
            "0",
            START + (i + 1) * HOUR - 1,
            "0",
            0,
            "0",
            "0",
            "0",
        ]
        for i in range(4)
    ]


class MarkRecoveryTest(unittest.TestCase):
    @unittest.skipUnless(
        importlib.util.find_spec("polars") or importlib.util.find_spec("pyarrow"),
        "Parquet backend required",
    )
    def test_partial_export_does_not_claim_complete_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = validate_response(json.dumps(payload()).encode(), job(), {})
            source = root / "mark_overlay.jsonl"
            source.write_text("".join(json.dumps(r) + "\n" for r in rows))
            (root / "summary.json").write_text(
                json.dumps(
                    {
                        "success": False,
                        "full_scope": True,
                        "overlay_sha256": digest(source.read_bytes()),
                        "target_hours": 3,
                        "verified_overlay_rows": 2,
                        "unresolved_hours": 1,
                        "source_conflicts": 0,
                        "plan_sha256": "test-plan",
                    }
                )
            )
            args = Namespace(recovery_dir=root, output_dir=root / "partial", allow_partial=True)
            export_overlay(args)
            manifest = json.loads((args.output_dir / "manifest.json").read_text())
            self.assertFalse(manifest["recovery_complete"])
            self.assertEqual(manifest["unresolved_hours"], 1)
            self.assertFalse(manifest["historical_strategy_eligible"])

    def test_incomplete_overlay_cannot_be_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "summary.json").write_text(json.dumps({"success": False}))
            with self.assertRaisesRegex(ValueError, "complete"):
                export_overlay(Namespace(recovery_dir=root, output_dir=root / "published"))
            self.assertFalse((root / "published").exists())

    @unittest.skipUnless(
        importlib.util.find_spec("polars") or importlib.util.find_spec("pyarrow"),
        "Parquet export uses existing research environment",
    )
    def test_versioned_export_preserves_exact_prices_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = validate_response(json.dumps(payload()).encode(), job(), {})
            source = root / "mark_overlay.jsonl"
            source.write_text("".join(json.dumps(r) + "\n" for r in rows))
            (root / "summary.json").write_text(
                json.dumps(
                    {
                        "success": True,
                        "full_scope": True,
                        "overlay_sha256": digest(source.read_bytes()),
                        "target_hours": 2,
                        "plan_sha256": "test-plan",
                    }
                )
            )
            args = Namespace(recovery_dir=root, output_dir=root / "published")
            export_overlay(args)
            if importlib.util.find_spec("polars"):
                import polars as pl

                frame = pl.read_parquet(args.output_dir / "mark_gap_overlay.parquet")
                actual = frame.to_dicts()
            else:
                import pyarrow.parquet as pq

                actual = pq.read_table(args.output_dir / "mark_gap_overlay.parquet").to_pylist()
            self.assertEqual(len(actual), 2)
            self.assertEqual([r["open_raw"] for r in actual], ["100", "100"])
            with self.assertRaisesRegex(ValueError, "never overwrite"):
                export_overlay(args)

    def test_only_exact_missing_keys_returned(self):
        rows = validate_response(json.dumps(payload()).encode(), job(), {})
        self.assertEqual([r["timestamp_ms"] for r in rows], job()["targets"])

    def test_partial_response_rejected(self):
        with self.assertRaisesRegex(ValueError, "partial"):
            validate_response(json.dumps(payload()[:-1]).encode(), job(), {})

    def test_seed_conflict_quarantined(self):
        seeds = {
            ("TESTUSDT", START + HOUR): {"open": "101", "high": "110", "low": "90", "close": "105"}
        }
        with self.assertRaises(SourceConflict) as caught:
            validate_response(json.dumps(payload()).encode(), job(), seeds)
        self.assertEqual(caught.exception.stamps, [START + HOUR])

    def test_lifecycle_context_does_not_create_eligibility(self):
        row = context_flags({"timestamp_ms": START + HOUR}, job())
        self.assertTrue(row["audit_after_known_lifecycle_end"])
        self.assertTrue(row["audit_after_last_positive_trade"])
        self.assertFalse(row["historical_strategy_eligible"])

    def test_seed_index_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seed.json"
            path.write_text("[]")
            with self.assertRaisesRegex(ValueError, "seed candidate index changed"):
                verified_seeds(
                    {"seed_candidates_path": str(path), "seed_candidates_sha256": "wrong"}
                )

    def test_corrupt_cached_response_fails_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            task = output / "jobs" / job()["job_id"]
            task.mkdir(parents=True)
            original = json.dumps(payload()).encode()
            raw = task / "response.raw"
            raw.write_bytes(original + b"tampered")
            query = urllib.parse.urlencode(
                {
                    "symbol": "TESTUSDT",
                    "interval": "1h",
                    "startTime": START,
                    "endTime": START + 4 * HOUR - 1,
                    "limit": 4,
                }
            )
            record = {
                "payload_path": str(raw),
                "sha256": digest(original),
                "bytes": len(original),
                "source_url": "https://fapi.binance.com/fapi/v1/markPriceKlines?" + query,
            }
            (task / "result.json").write_text(json.dumps({"status": "complete", "source": record}))
            with patch("recover_mark_gaps.ProbeClient.get", side_effect=AssertionError("network")):
                result = recover_job(job(), {}, output, RateGate())
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["new_requests"], 0)
            self.assertNotIn("rows", result)


if __name__ == "__main__":
    unittest.main()
