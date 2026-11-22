from __future__ import annotations

import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_history_extension as audit  # noqa: E402
from acquire_usdm_universe import audit_rows, digest, write_json  # noqa: E402


def fixture(root):
    source, data, output = root / "source", root / "data", root / "output"
    filename = "BTCUSDT-fundingRate-2020-01.zip"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            filename[:-4] + ".csv",
            "calc_time,funding_interval_hours,last_funding_rate\n1577836800000,8,0.0001\n",
        )
    body = stream.getvalue()
    row = {
        "key": "data/futures/um/monthly/fundingRate/BTCUSDT/" + filename,
        "symbol": "BTCUSDT",
        "kind": "funding",
        "month": "2020-01",
        "size": len(body),
        "has_checksum": True,
    }
    raw = data / "raw/binance_um_universe/funding/BTCUSDT" / filename
    raw.parent.mkdir(parents=True)
    raw.write_bytes(body)
    raw.with_name(filename + ".CHECKSUM").write_text(digest(body) + "  " + filename)
    metadata = {
        "sha256": digest(body),
        "byte_size": len(body),
        "source_url": "https://data.binance.vision/" + row["key"],
        "retrieved_at": "2026-11-19T00:00:00+00:00",
    }
    write_json(raw.with_name(filename + ".metadata.json"), metadata)
    report = {
        **row,
        "sha256": digest(body),
        "bytes": len(body),
        "source_url": metadata["source_url"],
        "retrieved_at": metadata["retrieved_at"],
        "path": "/home/other-host/data/raw/" + filename,
        "quality": audit_rows(body, filename, "funding", "2020-01"),
    }
    report_path = source / "download/files" / (digest(row["key"].encode()) + ".json")
    write_json(report_path, report)
    return source, data, output, row, raw, report_path, report


class EarlyHistoryAuditTests(unittest.TestCase):
    def test_interval_and_raw_rate(self):
        events = audit.funding_events([["1577836800000", "8", "0.00010000"]])
        self.assertEqual(events[0]["rate_raw"], "0.00010000")
        for interval in ("0", "-8", "1.5", "nan", "inf"):
            with self.assertRaises(ValueError):
                audit.funding_events([["1577836800000", interval, "0.1"]])

    def test_unknown_schema_not_inferred(self):
        with self.assertRaisesRegex(ValueError, "schema"):
            audit.funding_events([["1577836800000", "8", "0.1", "extra"]])

    def test_cross_month_jitter_retained(self):
        first = 1580515200000 - 8 * audit.HOUR
        events = [
            {"event_ms": first, "reported_interval_hours": 8, "rate_raw": "0.001"},
            {
                "event_ms": first + 8 * audit.HOUR + 20,
                "reported_interval_hours": 8,
                "rate_raw": "0.001",
            },
        ]
        result = audit.schedule(events)
        self.assertEqual(result["maximum_small_spacing_offset_ms"], 20)
        self.assertEqual(result["stable_interval_spacing_flags"], [])
        self.assertEqual(events[1]["event_ms"], first + 8 * audit.HOUR + 20)

    def test_schedule_gap_and_interval_change_are_distinct(self):
        events = [
            {
                "event_ms": 1577836800000 + offset * audit.HOUR,
                "reported_interval_hours": interval,
                "rate_raw": "0",
            }
            for offset, interval in ((0, 8), (16, 8), (20, 4))
        ]
        result = audit.schedule(events)
        self.assertEqual(len(result["stable_interval_spacing_flags"]), 1)
        self.assertEqual(len(result["interval_changes"]), 1)
        self.assertTrue(result["spacing_flags_are_not_proof_of_missing_settlements"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit.schedule([events[0], events[0]])

    def test_host_independent_path_and_verified_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            source, data, output, row, raw, _, _ = fixture(Path(folder))
            with patch.multiple(audit, SOURCE=source, DATA=data):
                result, cached = audit.check_file(row, output)
                self.assertFalse(cached)
                self.assertEqual(result["funding_events"][0]["reported_interval_hours"], 8)
                restored, cached = audit.check_file(row, output)
                self.assertTrue(cached)
                self.assertEqual(result, restored)
                self.assertEqual(audit.resolve_raw(row, data), raw)

    def test_raw_corruption_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            source, data, output, row, raw, _, _ = fixture(Path(folder))
            raw.write_bytes(raw.read_bytes() + b"corrupt")
            with (
                patch.multiple(audit, SOURCE=source, DATA=data),
                self.assertRaisesRegex(ValueError, "checksum"),
            ):
                audit.check_file(row, output)

    def test_quality_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            source, data, output, row, _, path, report = fixture(Path(folder))
            report["quality"]["row_count"] = 99
            write_json(path, report)
            with (
                patch.multiple(audit, SOURCE=source, DATA=data),
                self.assertRaisesRegex(ValueError, "quality"),
            ):
                audit.check_file(row, output)
