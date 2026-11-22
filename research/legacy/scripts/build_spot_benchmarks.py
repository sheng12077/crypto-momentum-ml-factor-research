"""Verified spot-price passive hold benchmarks, bounded to2021–2022."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from acquire_usdm_universe import verify_payload
from audit_development_continuity import sha
from reconcile_mark_gaps import ProbeClient, parse_payload
from recover_development_marks import Pace

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/first_development/v20261121_001/spot_benchmarks"
HOUR = 3600000
DAY = 86400000


def source(symbol, month, pace):
    folder = BASE / "raw" / symbol / month
    folder.mkdir(parents=True, exist_ok=True)
    meta_path = folder / "source.json"
    filename = f"{symbol}-1h-{month}.zip"
    url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{filename}"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        body = (folder / "archive.zip").read_bytes()
        checksum = (folder / "checksum.txt").read_bytes()
        verify_payload(body, checksum, filename, len(body))
        if meta["url"] != url or meta["sha256"] != sha(folder / "archive.zip"):
            raise ValueError("Spot cached metadata mismatch")
        return body, meta, 0
    attempt = folder / datetime.now(UTC).strftime("attempt_%Y%m%dT%H%M%S%fZ")
    client = ProbeClient(attempt)
    try:
        pace.wait()
        checksum = client.get("checksum", url + ".CHECKSUM", 4096)
        pace.wait()
        body = client.get("archive", url, 2 * 1024**2)
    finally:
        (attempt / "manifest.json").write_text(json.dumps(client.manifest, indent=2))
    verify_payload(body, checksum, filename, len(body))
    (folder / "archive.zip").write_bytes(body)
    (folder / "checksum.txt").write_bytes(checksum)
    meta = {"url": url, "sha256": sha(folder / "archive.zip"), "bytes": len(body),
            "retrieved_at": client.manifest[-1]["retrieved_at"]}
    meta_path.write_text(json.dumps(meta, indent=2))
    return body, meta, 2


def build():
    BASE.mkdir(parents=True, exist_ok=True)
    requests, compressed, provenance, quarantined = 0, 0, [], []
    gate = Pace()
    for symbol in ("BTCUSDT", "ETHUSDT"):
        observations = {}
        for year in (2021, 2022):
            for month in range(1, 13):
                text = f"{year}-{month:02d}"
                body, meta, new = source(symbol, text, gate)
                requests += new
                compressed += len(body)
                if requests > 128 or compressed > 64 * 1024**2:
                    raise ValueError("Spot acquisition budget exceeded")
                filename = f"{symbol}-1h-{text}.csv"
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    if archive.namelist() != [filename] or archive.infolist()[0].file_size > 10 * 1024**2:
                        raise ValueError("Unexpected spotZIPstructure/size")
                    rows = [r for r in csv.reader(io.StringIO(archive.read(filename).decode("utf-8-sig")))
                            if r and r[0] != "open_time"]
                start = int(datetime(year, month, 1, tzinfo=UTC).timestamp() * 1000)
                end = int(datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=UTC).timestamp() * 1000)
                complete = []
                for row in rows:
                    if (int(row[0]) <= int(row[6]) < int(row[0]) + HOUR - 1):
                        quarantined.append({"symbol": symbol, "month": text,
                                            "reason": "partial_hour_close_timestamp", "raw_row": row,
                                            "source_sha256": meta["sha256"]})
                    else:
                        complete.append(row)
                rows = complete
                parse_payload(json.dumps(rows).encode(), symbol, start, end - 1)
                for row in rows:
                    stamp = int(row[0])
                    if stamp in observations or not start <= stamp < end:
                        raise ValueError("Duplicate/out-of-month spot key")
                    observations[stamp] = {"close": float(row[4]), "volume": float(row[5]),
                                           "quote": float(row[7])}
                provenance.append({"symbol": symbol, "month": text, **meta})
                print(f"spot verified {symbol} {text}", flush=True)
        for year in (2021, 2022):
            start = int(datetime(year, 1, 1, tzinfo=UTC).timestamp() * 1000)
            final = int(datetime(2022, 12, 30, 23, tzinfo=UTC).timestamp() * 1000)
            end = int(datetime(2022, 12, 31, tzinfo=UTC).timestamp() * 1000)
            entry = observations[start + HOUR]
            exit_row = observations[final - HOUR]
            buy = entry["quote"] / entry["volume"] * 1.0005
            sell = exit_row["quote"] / exit_row["volume"] * .9995
            units = 100000 / (buy * 1.001)
            final_cash = units * sell * .999
            rows = []
            for day in range(start, end + 1, DAY):
                if day == start:
                    nav = 100000.
                elif day > final:
                    nav = final_cash
                else:
                    price = observations.get(day - HOUR)
                    if price is None:
                        raise ValueError("Missing spot benchmark valuation hour")
                    nav = units * price["close"]
                rows.append({"timestamp": datetime.fromtimestamp(day / 1000, UTC).strftime("%Y-%m-%dT00:00:00Z"),
                             "strategy_nav": nav})
            pd.DataFrame(rows).to_csv(BASE / f"{symbol}_{year}.csv", index=False)
            (BASE / f"{symbol}_{year}_ledger.json").write_text(json.dumps({
                "entry_fill": buy, "exit_fill": sell, "fixed_units": units,
                "entry_fee_usdt": units * buy * .001, "exit_fee_usdt": units * sell * .001,
                "final_nav": final_cash, "funding": 0, "passive_spot_identity": True}, indent=2))
    (BASE / "sources.json").write_text(json.dumps(provenance, indent=2))
    (BASE / "quarantined_rows.json").write_text(json.dumps(quarantined, indent=2))
    report = {"success": True, "new_http_requests": requests, "source_files": len(provenance),
              "compressed_bytes": compressed, "OOS_performance_inspected": False,
              "quarantined_partial_hours": len(quarantined),
              "registration_sha256": sha(ROOT / "experiments/006_spot_benchmark_correction.md"),
              "output_hashes": {p.name: sha(p) for p in BASE.glob("*.csv")}}
    (BASE / "summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    build()
