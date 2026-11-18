from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acquire_usdm_universe import digest, read_json, write_json  # noqa: E402
from screen_full_universe import prepare, quick_summary, scan_symbol, trade_report  # noqa: E402


def sample_data():
    symbols = ["AAAUSDT", "OLDUSDT", "DEADUSDT", "1000AAAUSDT"]
    ledger = [
        {
            "instrument_id": s,
            "current_noncoin_annotation": s == "AAAUSDT",
            "current_product_metadata": None if s == "OLDUSDT" else {},
            "known_identity_reuse": False,
        }
        for s in symbols
    ]
    quality = [
        {
            "symbol": s,
            "first_positive_trade_bar": None if s == "DEADUSDT" else "2021-01-01T00:00:00+00:00",
            "review_flags": [],
            "constant_zero_volume_trade_months": ["2021-02"] if s == "AAAUSDT" else [],
        }
        for s in symbols
    ]
    return {
        "ledger": ledger,
        "quality": quality,
        "cmc_queue": [
            {
                "instrument_id": s,
                "candidates_for_manual_review_only": [{"vendor_asset_id": 1}]
                if s == "AAAUSDT"
                else [],
            }
            for s in symbols
        ],
        "vendors": [{"vendor_asset_id": 1, "appearances": [{"date": "20210103"}]}],
        "episode_facts": {"records": []},
        "policy": {
            "vendor_updates": [],
            "sats": {"primary_historical_vendor_asset_id": 99},
            "whole_identifier_exclusions": [],
            "interval_exclusions": [],
            "rejected_vendor_associations": [],
        },
        "plan": {
            "files": [
                {"symbol": s, "kind": k, "month": "2021-01"}
                for s in symbols
                for k in ("trade", "mark", "funding")
                if s != "DEADUSDT"
            ]
        },
    }


def report_fixture(root, month="2021-01", positive=1):
    item = {
        "key": "data/AAA/" + month,
        "symbol": "AAAUSDT",
        "month": month,
        "kind": "trade",
        "size": 10,
    }
    value = {
        **item,
        "bytes": 10,
        "sha256": "raw-source",
        "quality": {
            "row_count": 2,
            "positive_volume_rows": positive,
            "zero_volume_rows": 2 - positive,
            "first_positive_volume_time": month + "-01T00:00:00+00:00" if positive else None,
            "last_positive_volume_time": month + "-02T00:00:00+00:00" if positive else None,
            "zero_volume_constant_trade_artifact": positive == 0,
        },
    }
    path = root / (digest(item["key"].encode()) + ".json")
    write_json(path, value)
    return item, path


class FullUniverseScreenTests(unittest.TestCase):
    def test_noncoin_missing_metadata_and_local_stub_do_not_delete_assets(self):
        records, _, _, _ = prepare(sample_data())
        by_id = {r["instrument_id"]: r for r in records}
        for symbol in ("AAAUSDT", "OLDUSDT"):
            self.assertEqual(by_id[symbol]["raw_data_disposition"], "retain_for_further_checks")
        self.assertFalse(by_id["DEADUSDT"]["positive_trade_observed"])
        self.assertEqual(by_id["AAAUSDT"]["stub_trade_months"], ["2021-02"])
        summary = quick_summary(records)
        self.assertEqual(summary["positive_trade_observed"], 3)
        self.assertFalse(summary["historical_eligible_universe_ready"])

    def test_scaled_prefix_needs_explicit_override(self):
        data = sample_data()
        records = {r["instrument_id"]: r for r in prepare(data)[0]}
        self.assertEqual(records["1000AAAUSDT"]["captured_vendor_IDs"], [])
        data["policy"]["vendor_updates"] = [
            {"instrument_id": "1000AAAUSDT", "proposed_vendor_asset_id": 1}
        ]
        records = {r["instrument_id"]: r for r in prepare(data)[0]}
        self.assertEqual(records["1000AAAUSDT"]["captured_vendor_IDs"], [1])

    def test_size_exclusion_does_not_remove_price_candidate(self):
        data = sample_data()
        data["policy"]["whole_identifier_exclusions"] = [
            {"instrument_id": "AAAUSDT", "scopes": ["size_join"]}
        ]
        record = next(r for r in prepare(data)[0] if r["instrument_id"] == "AAAUSDT")
        self.assertTrue(record["positive_trade_observed"])
        self.assertFalse(record["Size_history_lead_after_component_gate"])
        self.assertFalse(record["automatic_join_approved"])

    def test_report_identity_and_activity_count_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item, path = report_fixture(root)
            original = read_json(path)
            for mode in ("identity", "counts", "time"):
                value = copy.deepcopy(original)
                if mode == "identity":
                    value["symbol"] = "OTHERUSDT"
                elif mode == "counts":
                    value["quality"]["positive_volume_rows"] = 4
                else:
                    value["quality"]["last_positive_volume_time"] = None
                write_json(path, value)
                with self.assertRaises(ValueError):
                    trade_report(item, root)

    def test_monthly_checkpoint_resume_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports, output = root / "reports", root / "output"
            item, path = report_fixture(reports)
            stub, _ = report_fixture(reports, "2021-02", positive=0)
            record = next(r for r in prepare(sample_data())[0] if r["instrument_id"] == "AAAUSDT")
            history = {1: {"appearances": [{"date": "20210103"}, {"date": "20210207"}]}}
            arguments = (
                record,
                [item, stub],
                {},
                history,
                output,
                reports,
                "2020-01-01T00:00:00+00:00",
            )
            result, cached = scan_symbol(*arguments)
            self.assertFalse(cached)
            self.assertTrue(result["months"][0]["potential_Size_overlap_somewhere_in_month"])
            self.assertFalse(result["months"][1]["potential_Size_overlap_somewhere_in_month"])
            self.assertFalse(result["historical_strategy_eligible"])
            self.assertTrue(scan_symbol(*arguments)[1])
            (output / "checkpoints/AAAUSDT.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "checkpoint corrupted"):
                scan_symbol(*arguments)

    def test_changed_acquisition_report_invalidates_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item, path = report_fixture(root / "reports")
            record = next(r for r in prepare(sample_data())[0] if r["instrument_id"] == "AAAUSDT")
            arguments = (
                record,
                [item],
                {},
                {1: {"appearances": []}},
                root / "output",
                root / "reports",
                "2021-01-01T00:00:00+00:00",
            )
            scan_symbol(*arguments)
            value = read_json(path)
            value["retrieved_at"] = "changed-metadata"
            write_json(path, value)
            with self.assertRaisesRegex(ValueError, "reports changed"):
                scan_symbol(*arguments)


if __name__ == "__main__":
    unittest.main()
