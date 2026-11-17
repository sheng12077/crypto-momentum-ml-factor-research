import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import acquire_usdm_universe as acquisition  # noqa: E402


def make_archive(csv: str) -> tuple[dict, str, bytes, bytes]:
    row = {"symbol": "XUSDT", "kind": "trade", "month": "2024-01", "has_checksum": True}
    filename = "XUSDT-1h-2024-01.zip"
    row["key"] = acquisition.ROOTS["trade"] + "XUSDT/1h/" + filename
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr(filename[:-4] + ".csv", csv)
    body = target.getvalue()
    row["size"] = len(body)
    checksum = f"{acquisition.digest(body)}  {filename}\n".encode()
    return row, filename, body, checksum


class AcquisitionTest(unittest.TestCase):
    def test_concurrent_run_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lock"
            with acquisition.exclusive_run(path):
                with self.assertRaisesRegex(ValueError, "another acquisition"):
                    with acquisition.exclusive_run(path):
                        self.fail("second run should not acquire lock")

    def test_population_retains_unicode_and_missing_series(self):
        seed = {"roots": {k: {"all_symbols": []} for k in acquisition.KINDS}}
        seed["roots"]["trade"]["all_symbols"] = ["BTCUSDT", "测试USDT", "BTCUSDT_241227"]
        seed["roots"]["mark"]["all_symbols"] = ["OLDUSDT"]
        self.assertEqual(acquisition.choose_symbols(seed, None), ["BTCUSDT", "OLDUSDT", "测试USDT"])

    def test_current_classification_never_creates_historical_eligibility(self):
        record = acquisition.identity_record(
            "XUSDT",
            {},
            "seed",
            {},
            {"records": {"XUSDT": {"status": "TRADING", "underlyingType": "EQUITY"}}},
        )
        self.assertTrue(record["current_noncoin_annotation"])
        self.assertFalse(record["strategy_eligible"])
        self.assertIsNone(record["historical_contract_type"])

    def test_checksum_and_archive_size_fail_closed(self):
        row, filename, body, checksum = make_archive("1704067200000,1,1,1,1,1,0,1\n")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            acquisition.verify_payload(body + b"tampered", checksum, filename, row["size"])

    def test_same_output_cannot_change_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            acquisition.bind_run(Path(directory), {"seed": "a"})
            with self.assertRaisesRegex(ValueError, "different configuration"):
                acquisition.bind_run(Path(directory), {"seed": "b"})

    def test_arbitrary_archive_key_rejected(self):
        row, *_ = make_archive("")
        row["key"] = "https://untrusted.example/file.zip"
        with self.assertRaisesRegex(ValueError, "archive key"):
            acquisition.validate_file_record(row)

    def test_incomplete_census_cannot_download(self):
        with self.assertRaisesRegex(ValueError, "complete census"):
            acquisition.filter_plan({"complete_census": False, "files": []}, None, None)

    def test_structural_price_and_month_violations(self):
        for csv in ("1704067200000,2,1,1,1,1,0,1\n", "1706745600000,1,1,1,1,1,0,1\n"):
            _, filename, body, _ = make_archive(csv)
            with self.assertRaisesRegex(ValueError, "structural"):
                acquisition.audit_rows(body, filename, "trade", "2024-01")

    def test_verified_cache_resume_needs_no_network(self):
        row, filename, body, checksum = make_archive("1704067200000,1,1,1,1,0,0,0\n")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "raw/binance_um_universe/trade/XUSDT" / filename
            target.parent.mkdir(parents=True)
            target.write_bytes(body)
            target.with_name(filename + ".CHECKSUM").write_bytes(checksum)
            url = "https://data.binance.vision/" + row["key"]
            target.with_name(filename + ".metadata.json").write_text(
                json.dumps(
                    {
                        "sha256": acquisition.digest(body),
                        "archive_url": url,
                        "retrieved_at": "2026-11-17T00:00:00+00:00",
                    }
                )
            )
            with patch.object(acquisition.Discovery, "get", side_effect=AssertionError("network")):
                result = acquisition.acquire_file(row, root, root / "outputs")
            self.assertTrue(result["cache_hit"])
            self.assertTrue(result["quality"]["zero_volume_constant_trade_artifact"])
            target.write_bytes(body + b"tampered")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                acquisition.acquire_file(row, root, root / "outputs")


if __name__ == "__main__":
    unittest.main()
