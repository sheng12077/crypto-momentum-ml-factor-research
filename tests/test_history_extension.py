from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.parse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acquire_usdm_universe import audit_rows, digest, filter_plan, write_json  # noqa: E402
from check_universe_feasibility import ROOTS, S3  # noqa: E402
from extend_usdm_history import job_objects, pilot_files, selected_files, verify_plan  # noqa: E402
from probe_2019_history import START, assess  # noqa: E402


def objects(symbol="BTCUSDT", kind="funding", months=("2019-09", "2020-01", "2021-01")):
    name = "fundingRate" if kind == "funding" else "1h"
    prefix = ROOTS[kind] + symbol + "/" + ("" if kind == "funding" else "1h/")
    rows = []
    for month in months:
        key = f"{prefix}{symbol}-{name}-{month}.zip"
        rows.extend([{"key": key, "size": 100}, {"key": key + ".CHECKSUM", "size": 100}])
    return rows


def save_job(root, body, query=None):
    job = root / "jobs" / digest(b"BTCUSDT:funding")[:24]
    relative = "attempt/responses/listing_000.raw"
    (job / relative).parent.mkdir(parents=True, exist_ok=True)
    (job / relative).write_bytes(body)
    query = query or {"list-type": "2", "prefix": ROOTS["funding"] + "BTCUSDT/"}
    result = {
        "symbol": "BTCUSDT",
        "kind": "funding",
        "success": True,
        "manifest": [
            {
                "path": relative,
                "sha256": digest(body),
                "bytes": len(body),
                "status": 200,
                "source_url": S3 + "?" + urllib.parse.urlencode(query),
            }
        ],
    }
    write_json(job / "result.json", result)
    return job


def xml(truncated=False):
    return (
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<IsTruncated>{str(truncated).lower()}</IsTruncated>"
        + ("<NextContinuationToken>next</NextContinuationToken>" if truncated else "")
        + "</ListBucketResult>"
    ).encode()


class HistoryExtensionTests(unittest.TestCase):
    def test_2019_api_sample_does_not_prove_full_history(self):
        result = assess(
            [[START, "1", "2", "1", "1", "10", START + 3599999]], "trade", START, START + 3599999
        )
        self.assertTrue(result["sample_available"])
        self.assertFalse(result["full_2019_coverage_proven"])

    def test_2019_api_rejects_ignored_bounds(self):
        with self.assertRaisesRegex(ValueError, "bounds"):
            assess(
                [[START + 86400000, "1", "2", "1", "1", "10", START + 90000000]],
                "mark",
                START,
                START + 3599999,
            )

    def test_2019_api_funding_price_can_be_missing(self):
        result = assess(
            [{"symbol": "BTCUSDT", "fundingTime": START, "fundingRate": "0.001", "markPrice": ""}],
            "funding",
            START,
            START + 86400000,
        )
        self.assertTrue(result["sample_available"])
        self.assertFalse(result["all_sample_funding_mark_prices_present"])

    def test_2019_api_empty_and_error_payloads(self):
        self.assertFalse(assess([], "funding", START, START + 86400000)["sample_available"])
        with self.assertRaisesRegex(ValueError, "list"):
            assess({"code": -1}, "funding", START, START + 86400000)

    def test_old_window_does_not_filter_out_2019_download(self):
        files = selected_files("BTCUSDT", "funding", objects(), end="2020-12")
        self.assertEqual([r["month"] for r in files], ["2019-09", "2020-01"])
        self.assertEqual(
            filter_plan(
                {"complete_census": True, "official_checksum_gaps": 0, "files": files}, None, None
            ),
            files,
        )

    def test_exact_series_path_and_unicode_preserved(self):
        rows = objects("測試USDT", "trade", ("2020-01",))
        self.assertEqual(len(selected_files("測試USDT", "trade", rows)), 1)
        self.assertEqual(selected_files("BTCUSDT", "funding", objects(kind="mark")), [])

    def test_missing_checksum_is_explicit(self):
        rows = [r for r in objects() if not r["key"].endswith("CHECKSUM")]
        self.assertTrue(
            all(not r["has_checksum"] for r in selected_files("BTCUSDT", "funding", rows))
        )

    def test_pilot_selects_earliest_available_and_no_fake_series(self):
        files = [
            row
            for symbol in ("BTCUSDT", "ETHUSDT")
            for kind in ("trade", "mark", "funding")
            for row in selected_files(symbol, kind, objects(symbol, kind), end="2020-12")
        ]
        chosen = pilot_files(files)
        self.assertEqual(len(chosen), 6)
        self.assertTrue(all(r["month"] == "2019-09" for r in chosen))
        self.assertEqual(len(pilot_files(files[:1])), 1)
        with self.assertRaises(ValueError):
            pilot_files([])

    def test_cached_hash_and_url_are_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = save_job(root, xml())
            self.assertEqual(job_objects(root, "BTCUSDT", "funding", True)[0], [])
            (job / "attempt/responses/listing_000.raw").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "integrity"):
                job_objects(root, "BTCUSDT", "funding", True)
            save_job(root, xml(), {"list-type": "2", "prefix": "wrong"})
            with self.assertRaisesRegex(ValueError, "URL"):
                job_objects(root, "BTCUSDT", "funding", True)

    def test_incomplete_pagination_and_root_mismatch_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            save_job(root, xml(True))
            with self.assertRaisesRegex(ValueError, "pagination"):
                job_objects(root, "BTCUSDT", "funding", True)
            with self.assertRaisesRegex(ValueError, "membership"):
                job_objects(root, "BTCUSDT", "funding", False)

    def test_unsafe_evidence_path_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = save_job(root, xml())
            path = job / "result.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            result["manifest"][0]["path"] = "../listing_000.raw"
            write_json(path, result)
            with self.assertRaisesRegex(ValueError, "unsafe"):
                job_objects(root, "BTCUSDT", "funding", True)

    def test_2019_funding_csv_validation(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(
                "BTCUSDT-fundingRate-2019-09.csv",
                "calc_time,funding_interval_hours,last_funding_rate\n1569888000000,8,0.001\n",
            )
        # Timestamp is October1,so a September-labelled file must fail closed.
        with self.assertRaisesRegex(ValueError, "outside-month"):
            audit_rows(stream.getvalue(), "BTCUSDT-fundingRate-2019-09.zip", "funding", "2019-09")

    def test_modified_plan_rejected_before_acquisition(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_json(
                root / "summary.json",
                {
                    "success": True,
                    "raw_acquisition_plan_ready": True,
                    "plan_hashes": {"download_plan.json": "wrong"},
                },
            )
            write_json(root / "download_plan.json", {"files": []})
            with self.assertRaisesRegex(ValueError, "integrity"):
                verify_plan(root, "download_plan.json")
