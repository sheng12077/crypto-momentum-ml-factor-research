from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from build_early_research import save_table  # noqa: E402
from early_research_rules import (  # noqa: E402
    DAY,
    HOUR,
    START,
    api_table,
    daily_rows,
    daily_table,
    flags,
)


def policy():
    return {
        "launches": {
            "DEFIUSDT": START + 60 * DAY + 7 * HOUR,
            "AAVEUSDT": START + 90 * DAY + 7 * HOUR,
        },
        "settlements": {"LENDUSDT": START + 140 * DAY},
        "proposed_launches": {"QTUMUSDT": START + 50 * DAY + 8 * HOUR},
        "indices": ["DEFIUSDT"],
    }


def bars(days=122):
    rows = {
        START + d * DAY + h * HOUR: {
            "close": 1.0,
            "close_raw": "1.0000",
            "volume": 1.0,
            "quote_volume": 2.0,
            "taker_buy_quote_volume": 1.0,
        }
        for d in range(days)
        for h in range(24)
    }
    return rows, dict(rows)


class EarlyResearchTests(unittest.TestCase):
    def test_121_closes_and_raw_strings(self):
        trade, mark = bars()
        rows = daily_rows("BTCUSDT", trade, mark, [], policy())
        self.assertEqual(len(rows), 366)
        self.assertFalse(rows[119]["history_121_contiguous_closes"])
        self.assertTrue(rows[120]["history_121_contiguous_closes"])
        self.assertTrue(rows[120]["price_history_diagnostic_candidate"])
        self.assertEqual(rows[120]["trade_close_raw"], "1.0000")
        self.assertFalse(rows[120]["historical_strategy_eligible"])

    def test_missing_day_breaks_contiguity_not_endpoints(self):
        trade, mark = bars()
        for hour in range(24):
            trade.pop(START + 50 * DAY + hour * HOUR)
        rows = daily_rows("BTCUSDT", trade, mark, [], policy())
        self.assertTrue(rows[120]["history_120_endpoint_valid"])
        self.assertFalse(rows[120]["history_121_contiguous_closes"])
        self.assertIsNone(rows[50]["trade_volume_sum"])
        self.assertIsNone(rows[50]["trade_close"])

    def test_zero_activity_day_does_not_extend_history(self):
        trade, mark = bars()
        for hour in range(24):
            stamp = START + 50 * DAY + hour * HOUR
            trade[stamp] = {**trade[stamp], "volume": 0.0}
        rows = daily_rows("BTCUSDT", trade, mark, [], policy())
        self.assertFalse(rows[50]["valid_closing_observation"])
        self.assertFalse(rows[120]["history_121_contiguous_closes"])

    def test_confirmed_proposed_and_separate_contract_boundaries(self):
        rules = policy()
        before = START + 40 * DAY
        self.assertTrue(
            flags("QTUMUSDT", before, before + HOUR, rules)["audit_before_proposed_launch"]
        )
        self.assertFalse(
            flags("QTUMUSDT", before, before + HOUR, rules)["audit_before_confirmed_launch"]
        )
        self.assertTrue(
            flags("QTUMUSDT", before, before + HOUR, rules)["lifecycle_origin_unverified"]
        )
        after = rules["settlements"]["LENDUSDT"]
        self.assertTrue(
            flags("LENDUSDT", after, after + HOUR, rules)["audit_at_or_after_confirmed_settlement"]
        )
        self.assertFalse(
            flags("AAVEUSDT", after, after + HOUR, rules)["audit_at_or_after_confirmed_settlement"]
        )

    def test_api_interval_and_mark_remain_null_and_prelaunch_quarantined(self):
        rows = [
            {
                "event_timestamp_ms": START + 49 * DAY,
                "funding_rate_raw": "0.00010000",
                "reported_funding_interval_hours": None,
                "mark_price_raw": "",
            }
        ]
        table = api_table(
            rows,
            {
                "sha256": "abc",
                "url": "https://example.test",
                "retrieved_at": "2026-11-19T00:00:00+00:00",
            },
            policy(),
        )
        row = table.to_pylist()[0]
        self.assertIsNone(row["funding_interval_hours"])
        self.assertIsNone(row["funding_mark_price"])
        self.assertEqual(row["funding_mark_price_raw"], "")
        self.assertEqual(row["funding_rate_raw"], "0.00010000")
        self.assertTrue(row["quarantine_from_trading_reconstruction"])
        self.assertFalse(row["funding_payment_proven"])
        self.assertIsNone(row["available_at"])

    def test_funding_exact_reference_excluded_and_unknown_interval_not_fresh(self):
        trade, mark = bars(2)
        funding = [
            {
                "event_timestamp_ms": START + DAY - 8 * HOUR,
                "funding_rate_raw": "0.001",
                "funding_interval_hours": None,
                "quarantine_from_trading_reconstruction": False,
            },
            {
                "event_timestamp_ms": START + DAY,
                "funding_rate_raw": "0.002",
                "funding_interval_hours": 8,
                "quarantine_from_trading_reconstruction": False,
            },
        ]
        row = daily_rows("BTCUSDT", trade, mark, funding, policy())[0]
        self.assertEqual(row["latest_funding_rate_raw"], "0.001")
        self.assertFalse(row["funding_freshness_diagnostic"])

    def test_index_never_single_token_candidate_and_lend_stops_at_reference(self):
        trade, mark = bars(200)
        rules = policy()
        rows = daily_rows("DEFIUSDT", trade, mark, [], rules)
        self.assertTrue(rows[60]["partial_confirmed_lifecycle_day"])
        self.assertTrue(rows[190]["history_121_contiguous_closes"])
        self.assertFalse(rows[190]["price_history_diagnostic_candidate"])
        lend = daily_rows("LENDUSDT", trade, mark, [], rules)
        self.assertTrue(lend[138]["history_121_contiguous_closes"])
        self.assertTrue(lend[139]["audit_at_or_after_confirmed_settlement"])
        self.assertFalse(lend[139]["price_history_diagnostic_candidate"])
        self.assertFalse(lend[140]["valid_closing_observation"])

    def test_null_only_daily_schema_matches_populated_schema(self):
        trade, mark = bars()
        populated = daily_table(daily_rows("BTCUSDT", trade, mark, [], policy()))
        absent = daily_table(daily_rows("ETHUSDT", {}, {}, [], policy()))
        self.assertEqual(populated.schema, absent.schema)
        self.assertEqual(absent["trade_close"].null_count, 366)

    def test_equal_output_resume_and_corruption_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "x.parquet"
            table = pa.table({"x": [1, 2]})
            sha = save_table(target, table)
            self.assertEqual(sha, save_table(target, table))
            pq.write_table(pa.table({"x": [1, 3]}), target)
            with self.assertRaisesRegex(ValueError, "conflict"):
                save_table(target, table)
