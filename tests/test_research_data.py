import io
import json
import sys
import tempfile
import unittest
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from build_research_data import append_overlay, normalize_base, parse_csv  # noqa: E402
from momentum_data import DataUnavailableError, ResearchData  # noqa: E402

START = 1609459200000


def record(kind="trade"):
    return {
        "symbol": "TESTUSDT",
        "kind": kind,
        "sha256": "source",
        "source_url": "https://example.test",
        "retrieved_at": "2026-11-17T00:00:00+00:00",
        "quality": {"zero_volume_constant_trade_artifact": False},
    }


def bars():
    target = io.BytesIO()
    lines = [
        f"{START + i * 3600000},100.00000001,110,90,105,2,{START + (i + 1) * 3600000 - 1},210,1,1,105,0"
        for i in (0, 2)
    ]
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("sample.csv", "\n".join(lines))
    return normalize_base(parse_csv(target.getvalue(), "sample.zip", "trade"), record())


class ResearchDataTest(unittest.TestCase):
    def test_preserves_raw_price_and_availability_lower_bound(self):
        table = bars()
        self.assertEqual(table["open_raw"].to_pylist(), ["100.00000001"] * 2)
        self.assertEqual(
            table["available_at_lower_bound"][0].as_py(), datetime(2021, 1, 1, 1, tzinfo=UTC)
        )
        self.assertTrue(table["availability_is_lower_bound_only"][0].as_py())
        self.assertFalse(table["historical_strategy_eligible"][0].as_py())

    def test_funding_timestamp_jitter_and_rate_preserved(self):
        raw = pa.table(
            {
                "event_ms": [str(START + 2)],
                "funding_interval_hours": ["4"],
                "funding_rate": ["-0.00010000"],
            }
        )
        table = normalize_base(raw, record("funding"))
        self.assertEqual(table["event_timestamp_ms"][0].as_py(), START + 2)
        self.assertEqual(table["funding_rate_raw"][0].as_py(), "-0.00010000")
        self.assertEqual(table["cashflow_validity"][0].as_py(), "unverified_lifecycle")

    def test_overlay_cannot_replace_original_bar(self):
        with self.assertRaisesRegex(ValueError, "overwrite"):
            append_overlay(bars(), [{"timestamp_ms": START}], record("mark"))

    def test_reader_rejects_missing_hours_and_never_fills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"success": True}))
            (root / "lifecycle").mkdir()
            (root / "lifecycle/identity_ledger.json").write_text(
                json.dumps(
                    [
                        {
                            "instrument_id": "TESTUSDT",
                            "known_identity_reuse": False,
                            "official_events": [],
                        }
                    ]
                )
            )
            target = root / "observations/trade/TESTUSDT"
            target.mkdir(parents=True)
            pq.write_table(bars(), target / "2021-01.parquet")
            reader = ResearchData(root)
            start, end = datetime(2021, 1, 1, tzinfo=UTC), datetime(2021, 1, 1, 3, tzinfo=UTC)
            with self.assertRaises(DataUnavailableError):
                reader.bars("TESTUSDT", start, end)
            self.assertEqual(
                reader.bars("TESTUSDT", start, end, require_complete=False).num_rows, 2
            )
            with self.assertRaises(DataUnavailableError):
                reader.funding("TESTUSDT", start, end)

    def test_reader_rejects_identity_reuse_even_with_incomplete_reads(self):
        reader = ResearchData.__new__(ResearchData)
        reader._identities = {
            "LITUSDT": {
                "known_identity_reuse": True,
                "official_events": [
                    {"event_type": "launch", "effective_at": "2025-12-23T17:30:00+00:00"}
                ],
            }
        }
        with self.assertRaisesRegex(DataUnavailableError, "identity reuse"):
            reader.bars(
                "LITUSDT",
                datetime(2025, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 1, tzinfo=UTC),
                require_complete=False,
            )
        self.assertTrue(reader.lifecycle("LITUSDT")["known_identity_reuse"])

    def test_reader_rejects_terminal_event_crossing(self):
        reader = ResearchData.__new__(ResearchData)
        reader._identities = {
            "XUSDT": {
                "known_identity_reuse": False,
                "official_events": [
                    {
                        "event_type": "automatic_settlement",
                        "effective_at": "2025-01-01T09:00:00+00:00",
                    }
                ],
            }
        }
        with self.assertRaisesRegex(DataUnavailableError, "automatic settlement"):
            reader.bars(
                "XUSDT",
                datetime(2025, 1, 1, tzinfo=UTC),
                datetime(2025, 1, 2, tzinfo=UTC),
                require_complete=False,
            )

    def test_reader_rejects_naive_time(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            ResearchData._bounds("TESTUSDT", datetime(2021, 1, 1), datetime(2021, 1, 2))


if __name__ == "__main__":
    unittest.main()
