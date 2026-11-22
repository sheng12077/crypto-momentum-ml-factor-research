"""Independent raw-ZIP/Decimal readback; no HTTP or data mutation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/development_mark_recovery/v20261121_001"
FIELDS = ("open", "high", "low", "close")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(directory, cache, export):
    plan = json.loads((directory / "plan.json").read_text())
    manifest = json.loads((export / "manifest.json").read_text())
    if digest(directory / "plan.json") != manifest["plan_sha256"]:
        raise ValueError("Plan hash mismatch")
    path = export / "mark_gap_overlay.parquet"
    if digest(path) != manifest["overlay_sha256"]:
        raise ValueError("Overlay hash mismatch")
    source_rows, source_meta = {}, {}
    sources = json.loads((directory / "source_outcomes.json").read_text())
    jobs = {(j["symbol"], j["date"]): j for j in plan["jobs"]}
    for source in sources:
        if not source["success"]:
            continue
        symbol, day = source["symbol"], source["date"]
        key = hashlib.sha256(f"{symbol}:{day}".encode()).hexdigest()
        folder = (cache / "daily" / key).resolve()
        paths = [(folder / source[name]).resolve() for name in ("zip_path", "checksum_path")]
        if any(not p.is_relative_to(folder) for p in paths):
            raise ValueError("Cache path escape")
        body = paths[0].read_bytes()
        filename = f"{symbol}-1h-{day}.zip"
        checksum = paths[1].read_text().split()
        if (len(checksum) != 2 or checksum[1] != filename
                or checksum[0] != hashlib.sha256(body).hexdigest()
                or checksum[0] != source["source_sha256"]):
            raise ValueError("Raw ZIP/checksum mismatch")
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            if archive.namelist() != [filename[:-4] + ".csv"]:
                raise ValueError("Unexpected ZIP structure")
            raw = csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode("utf-8-sig")))
            seen = set()
            for item in raw:
                if not item or item[0] == "open_time":
                    continue
                stamp = int(item[0])
                if stamp in seen or stamp % 3_600_000:
                    raise ValueError("Invalid/duplicate raw hour")
                seen.add(stamp)
                if datetime.fromtimestamp(stamp / 1000, UTC).strftime("%Y-%m-%d") != day:
                    raise ValueError("Raw date mismatch")
                prices = [Decimal(x) for x in item[1:5]]
                if any(not p.is_finite() or p <= 0 for p in prices):
                    raise ValueError("Invalid raw prices")
                for field, number in zip(FIELDS, prices, strict=True):
                    old = jobs[(symbol, day)]["overlaps"].get(str(stamp))
                    if old and Decimal(old[field]) != number:
                        raise ValueError("Overlap conflict")
                source_rows[(symbol, stamp)] = item
                source_meta[(symbol, stamp)] = source
    rows = pq.read_table(path).to_pylist()
    observed = set()
    targets = {(j["symbol"], t) for j in plan["jobs"] for t in j["targets"]}
    for row in rows:
        key = row["instrument_id"], row["bar_open_ms"]
        if key not in targets or key in observed or key not in source_rows:
            raise ValueError("Unplanned/duplicate/unsourced overlay key")
        observed.add(key)
        item = source_rows[key]
        for i, field in enumerate(FIELDS, 1):
            if (Decimal(row[field + "_raw"]) != Decimal(item[i])
                    or not math.isfinite(row[field]) or row[field] != float(Decimal(item[i]))):
                raise ValueError("Raw/Parquet OHLC mismatch")
        if row["bar_close_ms"] != int(item[6]) or int(item[6]) != key[1] + 3_600_000 - 1:
            raise ValueError("Close timestamp mismatch")
        if row["bar_open_time"] != datetime.fromtimestamp(key[1] / 1000, UTC):
            raise ValueError("Open timestamp mismatch")
        for name in ("source_url", "source_sha256", "source_retrieved_at", "source_payload_path"):
            if row[name] != source_meta[key][name]:
                raise ValueError("Source provenance mismatch")
        if row["historical_strategy_eligible"] or row["publication_time_proven"]:
            raise ValueError("Unexpected eligibility/publication promotion")
    expected = targets & set(source_rows)
    missing = json.loads((export / "quality_mask.json").read_text())["missing_keys"]
    if observed != expected or set(map(tuple, missing)) != targets - observed:
        raise ValueError("Recovered/missing partition mismatch")
    if len(rows) != manifest["recovered_hours"] or len(missing) != manifest["unresolved_hours"]:
        raise ValueError("Manifest count mismatch")
    report = {"success": True, "independent_raw_readback_passed": True,
              "recovered_hours": len(rows), "unresolved_hours": len(missing),
              "recovery_complete": not missing, "overlay_sha256": digest(path),
              "source_http_requests": 0, "OOS_performance_inspected": False}
    (directory / "independent_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    directory = BASE / ("pilot" if args.pilot else "full")
    export = ROOT.parents[1] / "data/canonical/binance_um_development_mark_recovery" / (
        "v20261121_001_pilot" if args.pilot else "v20261121_001")
    validate(directory, BASE / "cache", export)


if __name__ == "__main__":
    main()
