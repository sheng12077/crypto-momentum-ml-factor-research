"""Checksum-verified, size-bounded lifecycle samples; no strategy performance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from check_universe_feasibility import Discovery

SAMPLES = (
    ("BTCUSDT", "trade", "2024-05"),
    ("BTCUSDT", "funding", "2024-05"),
    ("WAVESUSDT", "trade", "2024-05"),
    ("WAVESUSDT", "trade", "2024-06"),
    ("WAVESUSDT", "trade", "2026-10"),
    ("WAVESUSDT", "mark", "2026-10"),
    ("WAVESUSDT", "funding", "2025-06"),
    ("FTTUSDT", "trade", "2026-10"),
    ("FTTUSDT", "funding", "2025-06"),
    ("LUNAUSDT", "trade", "2022-05"),
    ("LUNAUSDT", "mark", "2022-06"),
    ("LUNAUSDT", "funding", "2022-05"),
)


def parse_zip(body: bytes, expected_csv: str, kind: str) -> dict:
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != expected_csv:
            raise ValueError("unexpected or multiple ZIP members")
        if members[0].file_size > 10 * 1024 * 1024:
            raise ValueError("uncompressed file exceeds 10 MiB")
        raw = archive.read(members[0])
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    if rows and rows[0] and rows[0][0] in ("open_time", "calc_time", "funding_time"):
        rows = rows[1:]
    timestamps, ohlc, rates = [], set(), []
    zero_volume, positive_volume, nonpositive_ohlc = 0, 0, 0
    first_positive = last_positive = None
    for row in rows:
        if len(row) < (3 if kind == "funding" else 8):
            raise ValueError("malformed CSV row")
        timestamp = int(row[0])
        timestamps.append(timestamp)
        if kind == "funding":
            rate = float(row[-1])
            if not math.isfinite(rate):
                raise ValueError("non-finite funding")
            rates.append(rate)
        else:
            prices = tuple(float(x) for x in row[1:5])
            volume, quote_volume = float(row[5]), float(row[7])
            if not all(math.isfinite(x) for x in (*prices, volume, quote_volume)):
                raise ValueError("non-finite bar")
            if volume < 0 or quote_volume < 0:
                raise ValueError("negative volume")
            ohlc.add(prices)
            nonpositive_ohlc += int(min(prices) <= 0)
            if volume > 0:
                positive_volume += 1
                first_positive = timestamp if first_positive is None else first_positive
                last_positive = timestamp
            else:
                zero_volume += 1
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("duplicate timestamps")
    if timestamps != sorted(timestamps):
        raise ValueError("non-monotonic timestamps")

    def iso(value: int | None) -> str | None:
        if value is None:
            return None
        divisor = 1_000_000 if value >= 100_000_000_000_000 else 1000
        return datetime.fromtimestamp(value / divisor, UTC).isoformat()

    return {
        "row_count": len(rows),
        "first_time": iso(timestamps[0]) if timestamps else None,
        "last_time": iso(timestamps[-1]) if timestamps else None,
        "positive_volume_rows": positive_volume if kind != "funding" else None,
        "zero_volume_rows": zero_volume if kind != "funding" else None,
        "first_positive_volume_time": iso(first_positive),
        "last_positive_volume_time": iso(last_positive),
        "distinct_ohlc_tuples": len(ohlc) if kind != "funding" else None,
        "constant_single_price": bool(ohlc) and len({p for values in ohlc for p in values}) == 1,
        "nonpositive_ohlc_rows": nonpositive_ohlc if kind != "funding" else None,
        "nonzero_funding_rows": sum(rate != 0 for rate in rates) if kind == "funding" else None,
    }


def run(metadata_path: Path, output: Path) -> dict:
    metadata = json.loads(metadata_path.read_text())
    selected = []
    for symbol, kind, month in SAMPLES:
        files = metadata["pilot"][symbol]["series"][kind]["files"]
        item = next(row for row in files if row["month"] == month)
        if item["size"] > 1024 * 1024 or not item["has_checksum"]:
            raise ValueError("sample exceeds size limit or lacks official checksum")
        selected.append((symbol, kind, month, item))
    if sum(item["size"] for _, _, _, item in selected) > 4 * 1024 * 1024:
        raise ValueError("combined ZIP budget exceeds 4 MiB")
    client = Discovery(output)
    result: dict = {
        "samples": [],
        "errors": [],
        "metadata_summary_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
    }
    for symbol, kind, month, item in selected:
        label = f"{symbol}_{kind}_{month}"
        try:
            filename = item["key"].rsplit("/", 1)[-1]
            url = "https://data.binance.vision/" + item["key"]
            checksum = client.get(label + "_checksum", url + ".CHECKSUM", 4096).decode().split()
            if len(checksum) != 2 or checksum[1].lstrip("*") != filename:
                raise ValueError("unexpected checksum record")
            body = client.get(label + "_zip", url, 1024 * 1024)
            if hashlib.sha256(body).hexdigest() != checksum[0]:
                raise ValueError("official checksum mismatch")
            if len(body) != item["size"]:
                raise ValueError("archive size changed since metadata discovery")
            summary = parse_zip(body, filename[:-4] + ".csv", kind)
            result["samples"].append(
                {
                    "symbol": symbol,
                    "kind": kind,
                    "month": month,
                    "checksum_verified": True,
                    "zip_bytes": len(body),
                    **summary,
                }
            )
            print(
                f"{label}: rows={summary['row_count']}, positive-volume="
                f"{summary['positive_volume_rows']}, nonzero-funding="
                f"{summary['nonzero_funding_rows']}",
                flush=True,
            )
        except Exception as exc:
            result["errors"].append({"sample": label, "error": str(exc)})
            print(f"{label}: ERROR {exc}", flush=True)
    controls = [s for s in result["samples"] if s["symbol"] == "BTCUSDT"]
    transport = len(result["samples"]) == 12 and not result["errors"] and len(controls) == 2
    transport = transport and all(s["row_count"] > 0 for s in controls)
    transport = transport and any(
        s["kind"] == "trade" and s["positive_volume_rows"] > 0 for s in controls
    )
    artifacts = [
        s
        for s in result["samples"]
        if s["symbol"] == "WAVESUSDT"
        and s["kind"] == "trade"
        and s["month"] == "2026-10"
        and s["row_count"] > 0
        and s["positive_volume_rows"] == 0
        and s["constant_single_price"]
    ]
    result["decision"] = {
        "transport_parsing_feasible": bool(transport),
        "late_file_artifact_supported": bool(artifacts),
        "full_download_ready": False,
        "historical_tradability_proven": False,
    }
    result["requests"] = len(client.manifest)
    result["response_bytes"] = sum(row["bytes"] for row in client.manifest)
    result["zip_bytes"] = sum(row["zip_bytes"] for row in result["samples"])
    for name, value in (("manifest.json", client.manifest), ("summary.json", result)):
        (output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["decision"], sort_keys=True), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.metadata_summary, args.output_dir)
