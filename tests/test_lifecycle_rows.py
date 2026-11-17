import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_lifecycle_rows import parse_zip  # noqa: E402


def zipped(text: str, name: str = "sample.csv") -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr(name, text)
    return target.getvalue()


class LifecycleRowsTest(unittest.TestCase):
    def test_constant_zero_volume_is_not_a_trade(self):
        summary = parse_zip(
            zipped("1704067200000,1,1,1,1,0,1704070799999,0\n"), "sample.csv", "trade"
        )
        self.assertEqual(summary["positive_volume_rows"], 0)
        self.assertTrue(summary["constant_single_price"])
        self.assertEqual(summary["first_time"], "2024-01-01T00:00:00+00:00")

    def test_duplicate_timestamps_rejected(self):
        row = "1704067200000,1,1,1,1,1,1704070799999,1\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_zip(zipped(row + row), "sample.csv", "trade")

    def test_unexpected_member_rejected(self):
        with self.assertRaisesRegex(ValueError, "members"):
            parse_zip(zipped("", "../sample.csv"), "sample.csv", "trade")

    def test_zero_funding_remains_an_observation(self):
        summary = parse_zip(
            zipped("calc_time,funding_interval_hours,last_funding_rate\n1704067200000,8,0\n"),
            "sample.csv",
            "funding",
        )
        self.assertEqual(summary["row_count"], 1)
        self.assertEqual(summary["nonzero_funding_rows"], 0)


if __name__ == "__main__":
    unittest.main()
