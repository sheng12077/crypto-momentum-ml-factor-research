import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acquire_usdm_universe import digest, write_json  # noqa: E402
from check_research_inputs import METRIC, fetch, funding_stats, parse_caps, parse_snapshot  # noqa: E402


def cap(asset="btc", value="100.000000001"):
    return {"asset": asset, "time": "2021-01-01T00:00:00.000000000Z", METRIC: value}


def snapshot(rows=None, title="03 January 2021"):
    rows = (
        rows
        if rows is not None
        else [
            {
                "id": 1,
                "name": "Bitcoin",
                "symbol": "BTC",
                "slug": "bitcoin",
                "circulatingSupply": "18000000",
                "quote": {
                    "USD": {
                        "lastUpdated": "2021-01-03T23:00:00Z",
                        "marketCap": "500000000001.000001",
                        "percentChange7d": 999999,
                    }
                },
            }
        ]
    )
    state = {"cryptocurrency": {"listingHistorical": {"data": rows}}}
    page = {"props": {"initialState": json.dumps(state)}}
    return (
        f"<title>Historical Snapshot - {title}</title>"
        + '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(page)
        + "</script>"
    ).encode()


class ResearchInputsTest(unittest.TestCase):
    def test_cap_exact_decimal_and_missing_are_not_filled(self):
        rows, missing = parse_caps({"data": [cap()]}, {"btc", "eth"}, "2021-01-01", "2021-01-01")
        self.assertEqual(rows[0]["market_cap_raw"], "100.000000001")
        self.assertEqual(len(missing), 1)
        self.assertIsNone(rows[0]["available_at"])

    def test_cap_duplicate_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_caps({"data": [cap(), cap()]}, {"btc"}, "2021-01-01", "2021-01-01")

    def test_cap_nonfinite_and_nonpositive_rejected(self):
        for number in ["0", "-1", "NaN", "Infinity"]:
            with self.subTest(number=number), self.assertRaises(ValueError):
                parse_caps({"data": [cap(value=number)]}, {"btc"}, "2021-01-01", "2021-01-01")

    def test_cap_pagination_cannot_claim_complete(self):
        with self.assertRaisesRegex(ValueError, "paginated"):
            parse_caps({"data": [], "next_page_url": "next"}, {"btc"}, "2021-01-01", "2021-01-01")

    def test_snapshot_only_extracts_cap_identity_not_performance(self):
        rows = parse_snapshot(snapshot(), "20210103")
        self.assertEqual(rows[0]["market_cap_decimal"], "500000000001.000001")
        self.assertNotIn("percentChange7d", rows[0])
        self.assertEqual(rows[0]["mapping_status"], "unverified")
        self.assertIsNone(rows[0]["available_at"])

    def test_snapshot_wrong_date_and_duplicates_rejected(self):
        with self.assertRaisesRegex(ValueError, "date/title"):
            parse_snapshot(snapshot(), "20240107")
        row = {
            "id": 1,
            "name": "Bitcoin",
            "symbol": "BTC",
            "slug": "bitcoin",
            "circulatingSupply": 1,
            "quote": {"USD": {"lastUpdated": "2021-01-03T23:00:00Z", "marketCap": 1}},
        }
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_snapshot(snapshot([row, row]), "20210103")

    def test_snapshot_future_observation_rejected(self):
        body = snapshot().replace(b"2021-01-03T23:00:00Z", b"2021-01-04T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "after requested"):
            parse_snapshot(body, "20210103")

    def test_funding_offset_and_after_end_flag_are_diagnostic_only(self):
        stamp = 1609459200000 + 20
        table = pa.table(
            {
                "event_timestamp_ms": [stamp],
                "funding_interval_hours": [8],
                "funding_rate_raw": ["0.00100"],
            }
        )
        result = funding_stats(
            table,
            {
                "official_events": [
                    {
                        "event_type": "automatic_settlement",
                        "effective_at": "2021-01-01T00:00:00+00:00",
                    }
                ]
            },
        )
        self.assertEqual(result["max_nearest_boundary_distance_ms"], 20)
        self.assertEqual(result["after_captured_settlement_without_captured_relaunch_ex_post"], 1)
        self.assertFalse(result["funding_cashflows_verified"])
        self.assertEqual(table["event_timestamp_ms"][0].as_py(), stamp)

    def test_funding_duplicate_rejected(self):
        table = pa.table(
            {
                "event_timestamp_ms": [1, 1],
                "funding_interval_hours": [8, 8],
                "funding_rate_raw": ["0", "0"],
            }
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            funding_stats(table, {"official_events": []})

    def test_cache_reuses_hash_valid_source_and_rejects_corruption(self):
        url, body = "https://example.test/public", b"sample"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = digest(url.encode())
            (root / (name + ".raw")).write_bytes(body)
            write_json(
                root / (name + ".json"),
                {"url": url, "bytes": len(body), "sha256": digest(body), "http_status": 200},
            )
            with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
                observed, report = fetch(url, root)
                self.assertEqual(observed, body)
                self.assertTrue(report["cache_hit"])
                (root / (name + ".raw")).write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    fetch(url, root)


if __name__ == "__main__":
    unittest.main()
