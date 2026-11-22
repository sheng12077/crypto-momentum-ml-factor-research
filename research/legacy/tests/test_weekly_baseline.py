from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from acquire_usdm_universe import digest  # noqa: E402
from check_weekly_baseline import COLUMNS, check_symbol, projected_rows  # noqa: E402
from weekly_contract import (  # noqa: E402
    COUNTS,
    millis,
    permitted,
    utc,
    validate_contract,
    weekly_calendar,
    weekly_flags,
)


def contract():
    return json.loads((ROOT / "config/weekly_baseline_v1.json").read_text(encoding="utf-8"))


def fixture():
    config = contract()
    start, end = utc("2021-01-02"), utc("2026-11-02")
    rows = []
    while start < end:
        rows.append(
            {
                "instrument_id": "BTCUSDT",
                "data_day": (start - timedelta(days=1)).date().isoformat(),
                "reference_time_ms": millis(start),
                **{key: key != "strict_four_factor_eligible" for key in COUNTS},
                "trade_close": 999.0,
            }
        )
        start += timedelta(days=1)
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(rows), sink)
    body = sink.getvalue().to_pybytes()
    return config, body, {"daily_sha256": digest(body), "rows": len(rows)}


class WeeklyCalendarTests(unittest.TestCase):
    def test_exact_registered_calendar(self):
        rows = weekly_calendar(contract())
        self.assertEqual(len(rows), 209)
        self.assertEqual(rows[0]["decision_date"], "2021-01-04")
        self.assertEqual(rows[-1]["decision_date"], "2024-12-30")
        for row in rows:
            self.assertLess(row["feature_cutoff_ms"], row["decision_ms"])
            self.assertEqual(row["decision_ms"], row["entry_window_start_ms"])
            self.assertEqual(row["entry_window_end_ms"] - row["decision_ms"], 3600000)
            self.assertEqual(row["exit_window_start_ms"] - row["decision_ms"], 7 * 86400000)
            self.assertEqual(row["label_assumed_available_ms"] - row["exit_window_end_ms"], 3600000)
            self.assertFalse(row["label_value_computed"])

    def test_boundary_purge_has_no_future_label_permission(self):
        config = contract()
        for row in weekly_calendar(config):
            for split in config["rounds"]:
                for purpose in ("train", "validation"):
                    if row[f"{split['name']}_{purpose}"] == "usable_by_time_only":
                        self.assertLess(
                            row["label_assumed_available_ms"], millis(utc(split[f"{purpose}_end"]))
                        )
        final = weekly_calendar(config)[-1]
        self.assertEqual(final["round_2_validation"], "purged_label_boundary")
        self.assertEqual(final["round_1_validation"], "outside_window")

    def test_exact_boundary_is_not_available_for_fit(self):
        self.assertEqual(
            permitted(utc("2022-12-26"), utc("2023-01-01"), "2021-01-01", "2023-01-01"),
            "purged_label_boundary",
        )
        self.assertEqual(
            permitted(utc("2023-01-01"), utc("2023-01-02"), "2021-01-01", "2023-01-01"),
            "outside_window",
        )

    def test_timezone_and_naive_timestamp(self):
        self.assertEqual(utc("2023-01-02T09:00:00+08:00"), utc("2023-01-02T01:00:00+00:00"))
        with self.assertRaisesRegex(ValueError, "timezone"):
            utc("2023-01-02T01:00:00")

    def test_changed_horizon_oos_or_splits_fail_closed(self):
        for key, value in (
            ("horizon_days", 14),
            ("oos_access_enabled", True),
            ("performance_enabled", True),
            ("decision_hour", 0),
            ("weekday", False),
        ):
            config = contract()
            config[key] = value
            with self.assertRaises(ValueError):
                weekly_calendar(config)
        config = contract()
        config["rounds"][1]["train_end"] = "2025-01-01"
        with self.assertRaisesRegex(ValueError, "split"):
            validate_contract(config)


class WeeklyCoverageTests(unittest.TestCase):
    def test_projection_excludes_prices_and_oos_rows(self):
        config, body, index = fixture()
        rows = projected_rows(body, "BTCUSDT", index, config)
        self.assertEqual(len(rows), 1460)
        self.assertEqual(set(rows[0]), set(COLUMNS))
        self.assertLess(max(row["reference_time_ms"] for row in rows), millis(utc("2025-01-01")))
        values = weekly_flags(rows, weekly_calendar(config), config)
        self.assertEqual(len(values), 209)
        self.assertTrue(all(row["four_factor_assumed_size_candidate"] for row in values))
        self.assertFalse(any(row["strict_four_factor_eligible"] for row in values))

    def test_corruption_wrong_count_and_identity_fail(self):
        config, body, index = fixture()
        for changed_body, changed_index, symbol in (
            (body + b"corrupt", index, "BTCUSDT"),
            (body, {**index, "rows": 1}, "BTCUSDT"),
            (body, index, "ETHUSDT"),
        ):
            with self.assertRaises(ValueError):
                projected_rows(changed_body, symbol, changed_index, config)

    def test_missing_duplicate_and_null_flags_fail(self):
        config, body, index = fixture()
        rows = projected_rows(body, "BTCUSDT", index, config)
        calendar = weekly_calendar(config)
        scheduled = next(
            row for row in rows if row["reference_time_ms"] == calendar[0]["feature_cutoff_ms"]
        )
        for invalid in (
            [row for row in rows if row is not scheduled],
            [*rows, scheduled],
            [
                {**row, "price_funding_data_candidate": None} if row is scheduled else row
                for row in rows
            ],
            [{**row, "data_day": "2021-01-01"} if row is scheduled else row for row in rows],
        ):
            with self.assertRaises(ValueError):
                weekly_flags(invalid, calendar, config)

    def test_direct_oos_injection_fails(self):
        config, body, index = fixture()
        rows = projected_rows(body, "BTCUSDT", index, config)
        with self.assertRaisesRegex(ValueError, "OOS guard"):
            weekly_flags(
                [*rows, {**rows[-1], "reference_time_ms": millis(utc("2025-01-01"))}],
                weekly_calendar(config),
                config,
            )

    def test_real_checkpoint_resume_and_tamper(self):
        config, body, index = fixture()
        calendar = weekly_calendar(config)
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "source", Path(folder) / "output"
            (source / "daily").mkdir(parents=True)
            (source / "daily/BTCUSDT.parquet").write_bytes(body)
            values, cached = check_symbol(source, output, "BTCUSDT", index, config, calendar)
            self.assertFalse(cached)
            restored, cached = check_symbol(source, output, "BTCUSDT", index, config, calendar)
            self.assertTrue(cached)
            self.assertEqual(values, restored)
            checkpoint = output / "instruments/BTCUSDT.json"
            altered = copy.deepcopy(json.loads(checkpoint.read_text(encoding="utf-8")))
            altered["weekly"][0]["price_funding_data_candidate"] = False
            checkpoint.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checkpoint"):
                check_symbol(source, output, "BTCUSDT", index, config, calendar)
