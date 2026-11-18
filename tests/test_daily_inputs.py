from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from acquire_usdm_universe import digest, write_json  # noqa: E402
from build_daily_inputs import read_partition, table_for  # noqa: E402
from daily_input_rules import (  # noqa: E402
    DAY,
    HOUR,
    make_daily,
    mapping_at,
    merge_hour,
    ms,
    size_at,
    size_schedule,
)

START = ms("2021-01-01T00:00:00+00:00")


def inputs(days=122):
    trade, mark, funding = {}, {}, []
    for day in range(days):
        for hour in range(24):
            stamp = START + day * DAY + hour * HOUR
            trade[stamp] = {
                "bar_open_ms": stamp,
                "close": 1.0,
                "close_raw": "1.000",
                "volume": 10.0,
                "quote_volume": 10.0,
                "taker_buy_volume": 4.0,
                "taker_buy_quote_volume": 4.0,
                "trade_count": 3,
                "source_recovered": False,
            }
            mark[stamp] = {
                "bar_open_ms": stamp,
                "close": 1.0,
                "close_raw": "1.0",
                "source_recovered": False,
            }
        funding.append(
            {
                "event_timestamp_ms": START + day * DAY + 16 * HOUR + 3,
                "funding_rate": 0.0001,
                "funding_rate_raw": "0.0001",
                "funding_interval_hours": 8,
            }
        )
    ledger = {"official_events": [], "current_noncoin_annotation": False}
    queue = {"candidates_for_manual_review_only": [{"vendor_asset_id": 1}]}
    facts = {"records": []}
    policy = {
        "research_window_from": "2020-01-01T00:00:00+00:00",
        "research_window_to": "2027-01-01T00:00:00+00:00",
        "whole_identifier_exclusions": [],
        "interval_exclusions": [],
        "feature_state_resets": [],
        "vendor_updates": [],
        "rejected_vendor_associations": [],
        "sats": {"primary_historical_vendor_asset_id": 28683},
        "later_SUN_launch": {"at_utc": "2024-08-22T13:05:00+00:00", "vendor_asset_id": 10529},
    }
    return trade, mark, funding, ledger, queue, facts, policy


def daily(values, days=122, schedules=None):
    return make_daily("TESTUSDT", START, START + days * DAY, *values, schedules or {})


def size_row(label="20210103"):
    return {
        "vendor_asset_id": 1,
        "snapshot_date": label,
        "market_cap_decimal": "100.0001",
        "available_at": None,
        "historical_content_version_proven": False,
    }


class DailyInputsTests(unittest.TestCase):
    def test_121_closes_are_needed_for_120_daily_intervals(self):
        rows = daily(inputs())
        self.assertFalse(rows[119]["history120_consecutive_complete"])
        self.assertTrue(rows[120]["history120_consecutive_complete"])
        self.assertTrue(rows[120]["price_funding_data_candidate"])
        self.assertFalse(rows[120]["strict_four_factor_eligible"])
        self.assertEqual(rows[120]["trade_close_raw"], "1.000")

    def test_missing_close_separates_endpoint_from_complete_history(self):
        values = inputs()
        del values[0][START + 50 * DAY + 23 * HOUR]
        rows = daily(values)
        self.assertTrue(rows[120]["history120_endpoint_valid"])
        self.assertFalse(rows[120]["history120_consecutive_complete"])
        self.assertFalse(rows[50]["trade_close_valid_for_history"])

    def test_launch_resets_history_and_partial_day(self):
        values = inputs(200)
        values[3]["official_events"] = [
            {"event_type": "launch", "effective_at": "2021-03-02T12:00:00+00:00"}
        ]
        rows = daily(values, 200)
        self.assertTrue(rows[60]["partial_lifecycle_day"])
        self.assertFalse(rows[120]["history120_consecutive_complete"])
        self.assertTrue(rows[180]["history120_consecutive_complete"])

    def test_closure_at_reference_blocks_orders_but_preserves_prior_close(self):
        values = inputs(3)
        values[3]["official_events"] = [
            {"event_type": "automatic_settlement", "effective_at": "2021-01-02T00:00:00+00:00"}
        ]
        rows = daily(values, 3)
        self.assertTrue(rows[0]["trade_close_valid_for_history"])
        self.assertTrue(rows[0]["known_lifecycle_order_block"])
        self.assertFalse(rows[1]["trade_close_valid_for_history"])

    def test_funding_keeps_jitter_and_excludes_equal_or_future_timestamp(self):
        values = inputs(2)
        values[2].extend(
            [
                {**values[2][0], "event_timestamp_ms": START + DAY},
                {**values[2][0], "event_timestamp_ms": START + DAY + 1},
            ]
        )
        row = daily(values, 2)[0]
        self.assertEqual(row["funding_event_ms"], START + 16 * HOUR + 3)
        self.assertEqual(row["funding_age_ms"], 8 * HOUR - 3)
        self.assertTrue(row["funding_within_reported_interval"])

    def test_funding_cannot_cross_episode(self):
        values = inputs(2)
        values[3]["official_events"] = [
            {"event_type": "launch", "effective_at": "2021-01-01T20:00:00+00:00"}
        ]
        self.assertFalse(daily(values, 2)[0]["funding_same_episode_observed"])

    def test_Size_assumption_has_no_future_access_or_unbounded_fill(self):
        schedules = size_schedule([size_row()])
        available = ms("2021-01-11T00:00:00+00:00")
        self.assertIsNone(size_at(1, available - 1, schedules))
        self.assertEqual(size_at(1, available, schedules)["market_cap_decimal"], "100.0001")
        self.assertIsNone(size_at(1, available + 7 * DAY, schedules))
        with self.assertRaises(ValueError):
            size_schedule([size_row(), size_row()])

    def test_stub_day_is_not_valid_history_and_incomplete_day_fails(self):
        values = inputs(3)
        for hour in range(24):
            values[0][START + hour * HOUR]["volume"] = 0
        del values[1][START + DAY + HOUR]
        rows = daily(values, 3)
        self.assertTrue(rows[0]["zero_activity_constant_day"])
        self.assertFalse(rows[0]["trade_close_valid_for_history"])
        self.assertEqual(rows[1]["mark_hours"], 23)
        self.assertNotEqual(rows[1]["base_failure_mask"] & 2, 0)

    def test_SUN_override_supersedes_unbounded_old_proposals(self):
        values = inputs(1)
        values[5]["records"] = [
            {
                "instrument_id": "SUNUSDT",
                "proposed_episodes": [
                    {"effective_from": None, "effective_to": None, "proposed_vendor_asset_id": 6990}
                ],
            }
        ]
        vendor, _ = mapping_at(
            "SUNUSDT", ms("2024-08-23T00:00:00+00:00"), values[4], values[5], values[6]
        )
        self.assertEqual(vendor, 10529)

    def test_legacy_restriction_requires_verified_consumption(self):
        values = inputs(1)
        values[6]["interval_exclusions"] = [
            {
                "instrument_id": "TESTUSDT",
                "scopes": ["regular_execution"],
                "from_utc": "2021-01-01T00:00:00+00:00",
                "to_utc": "2021-01-05T00:00:00+00:00",
                "reason": "verified_legacy_hours_not_integrated_into_existing_release",
            }
        ]
        self.assertTrue(daily(values, 1)[0]["scoped_execution_block"])
        row = make_daily("TESTUSDT", START, START + DAY, *values, {}, True)[0]
        self.assertFalse(row["scoped_execution_block"])
        target = {}
        original = next(iter(values[0].values()))
        merge_hour(target, original)
        self.assertFalse(merge_hour(target, dict(original)))
        with self.assertRaises(ValueError):
            merge_hour(target, {**original, "close": 2.0})

    def test_daily_schema_roundtrip_preserves_null_types(self):
        row = daily(inputs(1), 1)[0]
        table = table_for([row])
        self.assertEqual(table.schema.field("vendor_asset_id").type, pa.int64())
        self.assertEqual(table.schema.field("size_market_cap_decimal").type, pa.string())
        self.assertFalse(table["strict_four_factor_eligible"][0].as_py())

    def test_partition_hash_and_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            item = {
                "symbol": "TESTUSDT",
                "kind": "funding",
                "month": "2021-01",
                "key": "test-key",
                "size": 10,
            }
            relative = "observations/funding/TESTUSDT/2021-01.parquet"
            path = source / relative
            path.parent.mkdir(parents=True)
            table = pa.Table.from_pylist(inputs(1)[2])
            pq.write_table(table, path)
            index = {
                **item,
                "relative_path": relative,
                "parquet_sha256": digest(path.read_bytes()),
                "raw_sha256": "raw",
                "rows": 1,
                "overlay_rows": 0,
            }
            reports = source / "reports"
            write_json(
                reports / (digest(item["key"].encode()) + ".json"),
                {**item, "bytes": 10, "sha256": "raw", "quality": {"row_count": 1}},
            )
            write_json(source / "index" / (digest(item["key"].encode()) + ".json"), index)
            with (
                patch("build_daily_inputs.SOURCE", source),
                patch("build_daily_inputs.DOWNLOAD_REPORTS", reports),
            ):
                self.assertEqual(len(read_partition(item)[0]), 1)
                path.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    read_partition(item)


if __name__ == "__main__":
    unittest.main()
