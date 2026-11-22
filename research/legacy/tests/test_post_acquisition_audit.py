import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_usdm_acquisition import aggregate_symbol, gap_geometry, read_gap_ranges  # noqa: E402


class PostAcquisitionAuditTest(unittest.TestCase):
    def test_partial_first_month_is_boundary_not_interior(self):
        quality = {
            "row_count": 408,
            "first_time": "2024-01-15T00:00:00+00:00",
            "last_time": "2024-01-31T23:00:00+00:00",
            "missing_hourly_rows": 336,
        }
        result = gap_geometry(quality, "2024-01")
        self.assertEqual(result["classification"], "boundary_only")
        self.assertEqual(result["interior_missing"], 0)

    def test_mixed_boundary_and_interior_gap_not_hidden(self):
        quality = {
            "row_count": 25,
            "first_time": "2024-01-01T00:00:00+00:00",
            "last_time": "2024-01-02T02:00:00+00:00",
            "missing_hourly_rows": 719,
        }
        result = gap_geometry(quality, "2024-01")
        self.assertEqual(result["interior_missing"], 2)
        self.assertEqual(result["boundary_missing"], 717)

    def test_report_geometry_disagreement_rejected(self):
        with self.assertRaisesRegex(ValueError, "disagrees"):
            gap_geometry(
                {
                    "row_count": 744,
                    "first_time": "2024-01-01T00:00:00+00:00",
                    "last_time": "2024-01-31T23:00:00+00:00",
                    "missing_hourly_rows": 2,
                },
                "2024-01",
            )

    def test_exact_raw_gap_ranges(self):
        target = io.BytesIO()
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("sample.csv", "open_time,open\n1704067200000,1\n1704078000000,1\n")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.zip"
            path.write_bytes(target.getvalue())
            result = read_gap_ranges(path, 2)
        self.assertEqual(result[0]["missing_hours"], 2)

    def test_unknown_identity_never_becomes_eligible(self):
        result = aggregate_symbol(
            {
                "instrument_id": "OLDUSDT",
                "current_noncoin_annotation": False,
                "current_product_metadata": None,
            },
            [],
        )
        self.assertIn("identity_missing_from_current_snapshot", result["review_flags"])
        self.assertFalse(result["historical_strategy_eligible"])


if __name__ == "__main__":
    unittest.main()
