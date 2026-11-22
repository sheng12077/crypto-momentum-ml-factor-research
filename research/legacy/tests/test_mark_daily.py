import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from recover_mark_daily import day_keys, parse_daily  # noqa: E402

STAMP = 1609459200000
NAME = "TESTUSDT-1h-2021-01-01.zip"


def zipped(rows, member="TESTUSDT-1h-2021-01-01.csv"):
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr(member, "\n".join(",".join(map(str, row)) for row in rows))
    return target.getvalue()


def daily_row(stamp=STAMP):
    return [stamp, "100", "110", "90", "105", "0", stamp + 3599999, "0", 0, "0", "0", "0"]


class MarkDailyTest(unittest.TestCase):
    def test_daily_prices_remain_exact(self):
        values = parse_daily(zipped([daily_row()]), NAME, "2021-01-01")
        self.assertEqual(values[0][1], "100")

    def test_wrong_source_day_rejected(self):
        with self.assertRaisesRegex(ValueError, "date/schema"):
            parse_daily(zipped([daily_row(STAMP + 86400000)]), NAME, "2021-01-01")

    def test_daily_close_timestamp_validated(self):
        row = daily_row()
        row[6] = row[0]
        with self.assertRaisesRegex(ValueError, "close timestamp"):
            parse_daily(zipped([row]), NAME, "2021-01-01")

    def test_zip_member_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, "ZIP members"):
            parse_daily(zipped([daily_row()], "../unsafe.csv"), NAME, "2021-01-01")

    def test_boundary_days_included(self):
        keys = day_keys(
            {"symbol": "TESTUSDT", "prior_ms": STAMP - 3600000, "next_ms": STAMP + 86400000}
        )
        self.assertEqual([date for _, date in keys], ["2020-12-31", "2021-01-01", "2021-01-02"])


if __name__ == "__main__":
    unittest.main()
