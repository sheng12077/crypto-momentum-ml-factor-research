import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reconcile_mark_gaps import (
    HOUR,
    canonical_backfill_path,
    parse_payload,
    same_prices,
    source_path,
)  # noqa: E402

START = 1609459200000


def row(stamp=START):
    return [stamp, "100.00000001", "110", "90", "105", "0", stamp + HOUR - 1, "0", 0, "0", "0", "0"]


class MarkGapReconciliationTest(unittest.TestCase):
    def test_only_known_legacy_canonical_prefix_is_relocated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = canonical_backfill_path(
                root, "data/interim/binance_core_audit/series/btc_mark_bars/a.parquet"
            )
            self.assertEqual(
                path, root / "canonical/binance_core_audit/series/btc_mark_bars/a.parquet"
            )
            with self.assertRaisesRegex(ValueError, "outside"):
                canonical_backfill_path(root, "data/interim/other/a.parquet")

    def test_exact_hour_and_decimal_preserved(self):
        result = parse_payload(json.dumps([row()]).encode(), "BTCUSDT", START, START + HOUR - 1)
        self.assertEqual(result[0]["open"], "100.00000001")
        self.assertTrue(
            same_prices(
                result[0], {"open": "100.000000010", "high": "110.0", "low": "90", "close": "105"}
            )
        )

    def test_shifted_latest_response_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "out-of-range"):
            parse_payload(
                json.dumps([row(START + HOUR)]).encode(), "BTCUSDT", START, START + HOUR - 1
            )

    def test_wrong_interval_close_is_rejected(self):
        values = row()
        values[6] += HOUR
        with self.assertRaisesRegex(ValueError, "close timestamp"):
            parse_payload(json.dumps([values]).encode(), "BTCUSDT", START, START + HOUR - 1)

    def test_duplicate_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_payload(json.dumps([row(), row()]).encode(), "BTCUSDT", START, START + HOUR - 1)

    def test_empty_response_does_not_create_rows(self):
        self.assertEqual(parse_payload(b"[]", "BTCUSDT", START, START + HOUR - 1), [])

    def test_manifest_cannot_escape_expected_store(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "outside"):
                source_path(root, "../outside.json", root / "raw")


if __name__ == "__main__":
    unittest.main()
