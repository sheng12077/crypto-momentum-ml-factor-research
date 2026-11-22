"""Experiment009: same fixed-unit spot benchmark,2023 sources only."""

import csv
import io
import json
import zipfile
from datetime import UTC, datetime

import build_spot_benchmarks as original
import pandas as pd
from audit_development_continuity import sha
from prepare_validation_2023 import BASE, DAY, END, HOUR, START, write
from reconcile_mark_gaps import parse_payload
from recover_development_marks import Pace

SPOT = BASE / "spot_benchmarks"


def build():
    original.BASE = SPOT
    SPOT.mkdir(parents=True, exist_ok=True)
    pace = Pace()
    sources, quarantined = [], []
    requests = compressed = 0
    for symbol in ("BTCUSDT", "ETHUSDT"):
        observed = {}
        for month in range(1, 13):
            label = f"2023-{month:02d}"
            body, meta, new = original.source(symbol, label, pace)
            requests += new
            compressed += len(body)
            if requests > 64 or compressed > 32*1024**2:
                raise ValueError("2023spot acquisition budget exceeded")
            filename = f"{symbol}-1h-{label}.csv"
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                if archive.namelist() != [filename] or archive.infolist()[0].file_size > 10*1024**2:
                    raise ValueError("Invalid spot archive structure/size")
                raw = [r for r in csv.reader(io.StringIO(archive.read(filename).decode("utf-8-sig")))
                       if r and r[0] != "open_time"]
            first = int(datetime(2023, month, 1, tzinfo=UTC).timestamp()*1000)
            stop = int(datetime(2023 + (month == 12), month % 12 + 1, 1, tzinfo=UTC).timestamp()*1000)
            complete = []
            for row in raw:
                if int(row[0]) <= int(row[6]) < int(row[0])+HOUR-1:
                    quarantined.append({"symbol": symbol, "month": label, "raw_row": row,
                                        "source_sha256": meta["sha256"]})
                else:
                    complete.append(row)
            parse_payload(json.dumps(complete).encode(), symbol, first, stop-1)
            for row in complete:
                stamp = int(row[0])
                if stamp in observed:
                    raise ValueError("Duplicate spot timestamp")
                observed[stamp] = {"close": float(row[4]), "volume": float(row[5]), "quote": float(row[7])}
            sources.append({"symbol": symbol, "month": label, **meta})
            print(f"spot2023 verified {symbol}/{label}", flush=True)
        final, end = END-DAY-HOUR, END-DAY
        entry, exit_row = observed[START+HOUR], observed[final-HOUR]
        buy = entry["quote"]/entry["volume"]*1.0005
        sell = exit_row["quote"]/exit_row["volume"]*.9995
        units = 100000/(buy*1.001)
        cash = units*sell*.999
        rows = []
        for day in range(START, end+1, DAY):
            nav = 100000. if day == START else (cash if day > final else units*observed[day-HOUR]["close"])
            rows.append({"timestamp": datetime.fromtimestamp(day/1000, UTC).strftime("%Y-%m-%dT00:00:00Z"),
                         "strategy_nav": nav})
        pd.DataFrame(rows).to_csv(SPOT / f"{symbol}_2023.csv", index=False)
        write(SPOT / f"{symbol}_2023_ledger.json", {"entry_fill": buy, "exit_fill": sell,
              "fixed_units": units, "entry_fee_usdt": units*buy*.001, "exit_fee_usdt": units*sell*.001,
              "final_nav": cash, "funding": 0, "passive_spot_identity": True})
    write(SPOT / "sources.json", sources)
    write(SPOT / "quarantined_rows.json", quarantined)
    write(SPOT / "summary.json", {"success": True, "new_http_requests": requests, "source_files": len(sources),
          "compressed_bytes": compressed, "quarantined_partial_hours": len(quarantined),
          "sealed_2024_and_final_OOS_inspected": False,
          "output_hashes": {p.name: sha(p) for p in SPOT.glob("*.csv")}})


if __name__ == "__main__":
    build()
