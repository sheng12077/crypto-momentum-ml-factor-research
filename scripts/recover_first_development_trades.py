"""Recover all fixed-cohort trade/mark key mismatches before historical execution."""

from __future__ import annotations

import csv
import io
import json
import math
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from acquire_usdm_universe import verify_payload
from audit_development_continuity import sha
from reconcile_mark_gaps import ProbeClient, parse_payload
from recover_development_marks import Pace

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/first_development/v20261121_001/trade_recovery"
PREPARED = BASE.parent / "prepared"


def run():
    trades = pd.read_parquet(PREPARED / "trade.parquet")
    marks = pd.read_parquet(PREPARED / "mark.parquet")
    marks = marks[(marks.bar_open_ms >= 1609459200000) & (marks.bar_open_ms < 1672531200000)]
    observed = set(zip(trades.instrument_id, trades.bar_open_ms, strict=True))
    targets = {(r.instrument_id, int(r.bar_open_ms)) for r in marks.itertuples()
               if (r.instrument_id, r.bar_open_ms) not in observed}
    if len(targets) != 1440:
        raise ValueError("Registered trade target set changed")
    jobs = sorted({(s, datetime.fromtimestamp(t / 1000, UTC).strftime("%Y-%m-%d")) for s, t in targets})
    if len(jobs) != 60:
        raise ValueError("Expected60source-days")
    BASE.mkdir(parents=True, exist_ok=True)
    rows, sources, requests, compressed = [], [], 0, 0
    pace = Pace()
    for n, (symbol, day) in enumerate(jobs, 1):
        folder = BASE / "raw" / symbol / day
        folder.mkdir(parents=True, exist_ok=True)
        meta_path = folder / "source.json"
        filename = f"{symbol}-1h-{day}.zip"
        url = f"https://data.binance.vision/data/futures/um/daily/klines/{symbol}/1h/{filename}"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            body, checksum = (folder / "archive.zip").read_bytes(), (folder / "checksum.txt").read_bytes()
            verify_payload(body, checksum, filename, len(body))
            if sha(folder / "archive.zip") != meta["sha256"] or meta["url"] != url:
                raise ValueError("Trade cache mismatch")
        else:
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
            requests += 2
            (folder / "archive.zip").write_bytes(body)
            (folder / "checksum.txt").write_bytes(checksum)
            meta = {"url": url, "sha256": sha(folder / "archive.zip"),
                    "retrieved_at": client.manifest[-1]["retrieved_at"]}
            meta_path.write_text(json.dumps(meta, indent=2))
        compressed += len(body)
        if requests > 160 or compressed > 16 * 1024**2:
            raise ValueError("Trade recovery budget exceeded")
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            if archive.namelist() != [filename[:-4] + ".csv"] or archive.infolist()[0].file_size > 10 * 1024**2:
                raise ValueError("Unexpected trade ZIP structure")
            raw = [r for r in csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode("utf-8-sig")))
                   if r and r[0] != "open_time"]
        start = int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp() * 1000)
        parse_payload(json.dumps(raw).encode(), symbol, start, start + 86400000 - 1)
        for r in raw:
            stamp = int(r[0])
            volume, quote, buy = float(r[5]), float(r[7]), float(r[10])
            if not all(math.isfinite(v) and v >= 0 for v in (volume, quote, buy)) or buy > quote * (1 + 1e-9):
                raise ValueError("Invalid recovered trade volume")
            if (symbol, stamp) not in targets:
                raise ValueError("Unexpected recovery key")
            rows.append({"instrument_id": symbol, "bar_open_ms": stamp, "close": float(r[4]),
                         "volume": volume, "quote_volume": quote, "taker_buy_quote_volume": buy,
                         "close_raw": r[4], "volume_raw": r[5], "quote_volume_raw": r[7],
                         "taker_buy_quote_volume_raw": r[10],
                         "source_url": url, "source_sha256": meta["sha256"],
                         "source_retrieved_at": meta["retrieved_at"]})
        sources.append({"symbol": symbol, "date": day, **meta})
        if n % 10 == 0:
            print(f"trade recovery {n}/{len(jobs)}", flush=True)
    keys = [(r["instrument_id"], r["bar_open_ms"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != targets:
        raise ValueError("Recovered trade keys do not exactly cover registered targets")
    rows.sort(key=lambda r: (r["instrument_id"], r["bar_open_ms"]))
    path = BASE / "trade_overlay.parquet"
    pq.write_table(pa.Table.from_pylist(rows), path, compression="zstd")
    if pq.read_table(path).to_pylist() != rows:
        raise ValueError("Trade overlay Parquet roundtrip mismatch")
    (BASE / "sources.json").write_text(json.dumps(sources, indent=2))
    report = {"success": True, "recovered_hours": len(rows), "unresolved_hours": 0,
              "source_days": len(jobs), "new_http_requests": requests,
              "overlay_sha256": sha(path), "OOS_performance_inspected": False,
              "registration_sha256": sha(ROOT / "experiments/007_execution_trade_source_repair.md")}
    (BASE / "summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    run()
