"""Actual spot benchmarks; source timestamps normalized before validation."""
import csv
import io
import json
import zipfile
from datetime import UTC, datetime

import pandas as pd
from audit_development_continuity import sha
from final_holdout_acquisition import Archives
from final_holdout_common import BASE, DAY, HOUR, WINDOWS, bind, checked_manifest, code_contract, months, ms, write
from reconcile_mark_gaps import parse_payload

SPOT = BASE / "spot_benchmarks"


def normalize_row(raw):
    row = list(raw)
    unit = "us" if int(row[0]) >= 100_000_000_000_000 else "ms"
    divisor = 1000 if unit == "us" else 1
    if int(row[0]) % divisor:
        raise ValueError("Open timestamp not millisecond aligned")
    row[0], row[6] = str(int(row[0])//divisor), str(int(row[6])//divisor)
    return row, unit


def benchmark(observed, start, stop):
    last, final = stop-DAY, stop-DAY-HOUR
    entry, exit_row = observed[start+HOUR], observed[final-HOUR]
    if entry["volume"] <= 0 or exit_row["volume"] <= 0:
        raise ValueError("Missing spot execution volume")
    buy, sell = entry["quote"]/entry["volume"]*1.0005, exit_row["quote"]/exit_row["volume"]*.9995
    units = 100000/(buy*1.001)
    cash = units*sell*.999
    rows = [{"timestamp": datetime.fromtimestamp(t/1000, UTC).strftime("%Y-%m-%dT00:00:00Z"),
             "strategy_nav": 100000. if t == start else cash if t > final else units*observed[t-HOUR]["close"]}
            for t in range(start, last+1, DAY)]
    return pd.DataFrame(rows), {"entry_fill": buy, "exit_fill": sell, "fixed_units": units,
        "entry_fee": units*buy*.001, "exit_fee": units*sell*.001, "final_nav": cash}


def build():
    bind(BASE / "code_contract.json", code_contract())
    if (SPOT / "summary.json").exists():
        checked_manifest(SPOT, "summary.json")
        print('{"success": true, "stage": "spot", "cache_hit": true}')
        return
    client = Archives(SPOT / "raw", 128, 64*1024**2, 44)
    sources, quarantine = [], []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        observed = {}
        for month in months():
            filename = f"{symbol}-1h-{month}"
            url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{filename}.zip"
            body, meta = client.fetch(f"{symbol}/{month}", url)
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                if archive.namelist() != [filename+".csv"] or archive.infolist()[0].file_size > 10*1024**2:
                    raise ValueError("Unexpected spot member")
                raw = [r for r in csv.reader(io.StringIO(archive.read(filename+".csv").decode("utf-8-sig")))
                       if r and r[0] != "open_time"]
            complete, units = [], set()
            for raw_row in raw:
                row, unit = normalize_row(raw_row)
                units.add(unit)
                if int(row[0]) <= int(row[6]) < int(row[0])+HOUR-1:
                    quarantine.append({"symbol": symbol, "month": month, "raw_row": raw_row})
                else:
                    complete.append(row)
            if len(units) != 1:
                raise ValueError("Mixed spot timestamp units")
            year, number = map(int, month.split("-"))
            start, stop = ms(month+"-01"), ms(f"{year+(number == 12)}-{number%12+1:02d}-01")
            parse_payload(json.dumps(complete).encode(), symbol, start, stop-1)
            for row in complete:
                stamp = int(row[0])
                if stamp in observed:
                    raise ValueError("Duplicate spot hour")
                observed[stamp] = {"close": float(row[4]), "volume": float(row[5]), "quote": float(row[7])}
            sources.append({"symbol": symbol, "month": month, "source_units": list(units), **meta})
            print(f"verified spot {symbol}/{month}", flush=True)
        for name, (start, stop) in WINDOWS.items():
            daily, ledger = benchmark(observed, start, stop)
            daily.to_csv(SPOT / f"{symbol}_{name}.csv", index=False)
            write(SPOT / f"{symbol}_{name}_ledger.json", ledger)
    write(SPOT / "sources.json", sources)
    write(SPOT / "quarantined_rows.json", quarantine)
    write(SPOT / "summary.json", {"success": True, "source_files": len(sources),
        "code_contract_sha256": sha(BASE / "code_contract.json"),
        "output_hashes": {p.name: sha(p) for p in SPOT.iterdir() if p.is_file() and p.name != "summary.json"}})


if __name__ == "__main__":
    build()
