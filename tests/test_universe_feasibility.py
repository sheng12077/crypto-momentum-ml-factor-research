"""Guard incomplete metadata and misleading availability claims."""

import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "feasibility", Path(__file__).resolve().parents[1] / "scripts/check_universe_feasibility.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FeasibilityTest(unittest.TestCase):
    def test_truncated_listing_fails_closed(self):
        body = b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>true</IsTruncated></ListBucketResult>'
        with self.assertRaisesRegex(ValueError, "continuation"):
            MODULE.parse_listing(body)

    def test_non_listing_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.parse_listing(b"<Error><Message>Access denied</Message></Error>")

    def test_pagination_and_sizes(self):
        body = b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>true</IsTruncated><NextContinuationToken>abc</NextContinuationToken><Contents><Key>a.zip</Key><Size>12</Size></Contents></ListBucketResult>'
        _, objects, token = MODULE.parse_listing(body)
        self.assertEqual((objects, token), ([{"key": "a.zip", "size": 12}], "abc"))

    def test_coverage_excludes_outside_window_and_other_symbols(self):
        keys = [
            "XUSDT-1h-2020-12.zip",
            "XUSDT-1h-2021-01.zip",
            "XUSDT-1h-2021-01.zip.CHECKSUM",
            "XUSDT-1h-2021-03.zip",
            "YUSDT-1h-2021-02.zip",
            "XUSDT-1h-2026-11.zip",
        ]
        summary = MODULE.summarize_files("XUSDT", "trade", [{"key": k, "size": 10} for k in keys])
        self.assertEqual(summary["months"], ["2021-01", "2021-03"])
        self.assertEqual(summary["missing_interior_months"], ["2021-02"])
        self.assertEqual(summary["checksum_gaps"], ["2021-03"])

    def test_token_cycle_fails_closed(self):
        client = MODULE.Discovery.__new__(MODULE.Discovery)
        client.get = lambda *_: (
            b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>true</IsTruncated><NextContinuationToken>same</NextContinuationToken></ListBucketResult>'
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            client.listing("test", "prefix")


if __name__ == "__main__":
    unittest.main()
