from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from inventory_early_size import (  # noqa: E402
    available,
    dates,
    decision_times,
    literal_match,
    snapshot_at,
    summarize,
)


def ms(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp() * 1000)


def panel(index=False):
    symbol = "DEFIUSDT" if index else "BTCUSDT"
    return {
        symbol: {
            reference: {
                "valid_closing_observation": True,
                "complete_trade_day": True,
                "price_history_diagnostic_candidate": not index,
                "funding_freshness_diagnostic": True,
                "known_composite_index": index,
                "audit_at_or_after_confirmed_settlement": False,
            }
            for reference in decision_times()
        }
    }


def cap(vendor=1, symbol="BTC", name="Bitcoin"):
    return {"vendor_asset_id": vendor, "symbol": symbol, "name": name}


class EarlySizeTests(unittest.TestCase):
    def test_frozen_calendar_and_decisions(self):
        labels = dates()
        self.assertEqual(len(labels), 54)
        self.assertEqual(labels[:3], ["20191222", "20191229", "20200105"])
        self.assertEqual(labels[-1], "20201227")
        self.assertEqual(len(decision_times()), 52)
        self.assertEqual(decision_times()[-1], ms("2020-12-28"))

    def test_lag_and_strict_expiry(self):
        self.assertEqual(available("20191229"), ms("2020-01-06"))
        self.assertEqual(snapshot_at(ms("2020-01-01"), dates()), "20191222")
        self.assertEqual(snapshot_at(ms("2020-01-06"), dates()), "20191229")
        self.assertIsNone(snapshot_at(ms("2020-01-13"), ["20191229"]))
        self.assertEqual(snapshot_at(ms("2020-01-13"), dates()), "20200105")

    def test_same_date_ambiguity_and_index_not_joined(self):
        self.assertEqual(literal_match("BTCUSDT", [cap()])[0], "literal_unverified")
        self.assertEqual(literal_match("BTCUSDT", [cap(), cap(2)])[0], "ambiguous_same_date")
        self.assertEqual(
            literal_match("DEFIUSDT", [cap(3, "DEFI")], True), ("excluded_composite_index", [])
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            literal_match("BTCUSDT", [cap(), cap()])

    def test_future_vendor_id_not_used_for_earlier_snapshot(self):
        weekly, review = summarize(panel(), {"20191229": [cap(1)], "20200105": [cap(2)]}, dates())
        self.assertEqual(weekly[0]["literal_size_price_history_leads"], 1)
        self.assertEqual(weekly[1]["literal_size_price_history_leads"], 1)
        self.assertTrue(review[0]["literal_IDs_change_or_multiple"])
        self.assertIsNone(review[0]["approved_historical_mapping"])

    def test_uncaptured_snapshot_not_replaced_by_old_asset_cap(self):
        weekly, _ = summarize(panel(), {"20191229": [cap()]}, dates())
        self.assertTrue(weekly[0]["snapshot_captured"])
        self.assertFalse(weekly[1]["snapshot_captured"])
        self.assertEqual(weekly[1]["literal_size_price_history_leads"], 0)

    def test_name_only_proposal_is_not_literal_coverage(self):
        sample = panel()
        sample["IOTAUSDT"] = sample.pop("BTCUSDT")
        weekly, review = summarize(sample, {"20191229": [cap(1720, "MIOTA", "IOTA")]}, dates())
        self.assertEqual(weekly[0]["literal_size_price_history_leads"], 0)
        self.assertIn("1720", review[0]["name_only_proposals_not_joins"])

    def test_composite_index_not_active_single_token_or_size_lead(self):
        weekly, review = summarize(
            panel(True), {"20191229": [cap(3, "DEFI", "DEFI token")]}, dates()
        )
        self.assertEqual(weekly[0]["active_single_token_diagnostic"], 0)
        self.assertEqual(weekly[0]["literal_size_price_history_leads"], 0)
        self.assertEqual(review[0]["literal_vendor_proposals"], {})
