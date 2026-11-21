"""Verified daily-archive recovery of active-trade mark gaps, 2021–2022 only."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from acquire_usdm_universe import exclusive_run
from audit_development_continuity import sha
from reconcile_mark_gaps import HOUR, parse_ohlc, parse_payload, same_prices
from recover_mark_daily import daily_source

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parents[1] / "data/canonical"
DAILY = DATA / "binance_um_daily_research/v20261118_001"
HOURLY = DATA / "binance_um_research/v20261117_001"
BASE = ROOT / "data/interim/development_mark_recovery/v20261121_001"
FIELDS = ("open", "high", "low", "close")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bound_write(path, value):
    if path.exists() and json.loads(path.read_text()) != value:
        raise ValueError(f"Immutable inputs changed: {path}; choose a new directory")
    write(path, value)


def valid_stamps(rows, symbol):
    result = {}
    for row in rows:
        stamp = row["bar_open_ms"]
        if row["instrument_id"] != symbol or stamp % HOUR or stamp in result:
            raise ValueError("Identifier, duplicate or off-grid hourly source")
        result[stamp] = row
    return result


def classify(stamp, marks):
    if not marks:
        return "whole_month_absent"
    return "leading" if stamp < min(marks) else "trailing" if stamp > max(marks) else "interior"


def partition(symbol, month, kind, source_index):
    prefix = "klines" if kind == "trade" else "markPriceKlines"
    key = f"data/futures/um/monthly/{prefix}/{symbol}/1h/{symbol}-1h-{month}.zip"
    path = HOURLY / "observations" / kind / symbol / f"{month}.parquet"
    expected = source_index["sources"].get(key)
    if expected is None:
        if path.exists():
            raise ValueError("Unbound hourly partition exists")
        return {}, {"missing_partition": True}
    if not path.exists() or sha(path) != expected["parquet_sha256"]:
        raise ValueError(f"Hourly integrity failure: {symbol}/{kind}/{month}")
    columns = ["instrument_id", "bar_open_ms", "volume"] if kind == "trade" else [
        "instrument_id", "bar_open_ms", *[f"{f}_raw" for f in FIELDS]]
    rows = pq.read_table(path, columns=columns).to_pylist()
    return valid_stamps(rows, symbol), {"parquet_sha256": expected["parquet_sha256"], "key": key}


def make_plan(directory, pilot=False):
    symbols = sorted(p.stem for p in (DAILY / "daily").glob("*.parquet"))
    if len(symbols) != 924:
        raise ValueError("Expected 924 daily identifiers")
    if pilot:
        symbols = ["BTCUSDT"]
    jobs, bindings = [], {}
    for number, symbol in enumerate(symbols, 1):
        index_path = DAILY / "index" / f"{symbol}.json"
        index = json.loads(index_path.read_text())
        path = DAILY / "daily" / f"{symbol}.parquet"
        if index["instrument_id"] != symbol or sha(path) != index["daily_sha256"]:
            raise ValueError("Daily index/hash mismatch")
        rows = pq.read_table(path, columns=["data_day", "trade_hours", "mark_hours"],
                             filters=[("data_day", ">=", "2021-01-01"),
                                      ("data_day", "<", "2023-01-01")]).to_pylist()
        days = {r["data_day"] for r in rows if r["trade_hours"] > 0 and r["mark_hours"] < 24}
        if pilot:
            days &= {"2022-07-31"}
        partitions = {}
        for month in sorted({day[:7] for day in days}):
            trades, tb = partition(symbol, month, "trade", index)
            marks, mb = partition(symbol, month, "mark", index)
            partitions[month] = {"trade": tb, "mark": mb}
            for day in sorted(d for d in days if d[:7] == month):
                start = int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp() * 1000)
                targets = sorted(t for t, row in trades.items()
                                 if start <= t < start + 24 * HOUR and t not in marks
                                 and row["volume"] is not None
                                 and math.isfinite(row["volume"]) and row["volume"] > 0)
                if not targets:
                    continue
                existing = {str(t): parse_ohlc([r[f"{f}_raw"] for f in FIELDS])
                            for t, r in marks.items() if start <= t < start + 24 * HOUR}
                jobs.append({"symbol": symbol, "date": day, "targets": targets,
                             "overlaps": existing,
                             "gap_class_counts": dict(Counter(classify(t, marks) for t in targets))})
        bindings[symbol] = {"daily_sha256": index["daily_sha256"],
                            "index_sha256": sha(index_path), "hourly_partitions": partitions}
        if number % 100 == 0:
            print(f"inventory {number}/{len(symbols)}", flush=True)
    plan = {"schema": 1, "scope": "pilot" if pilot else "full", "jobs": jobs,
            "source_bindings": bindings, "target_hours": sum(len(j["targets"]) for j in jobs),
            "source_days": len(jobs), "identifiers_screened": len(symbols),
            "registration_sha256": sha(ROOT / "experiments/004_development_mark_boundary_recovery.md")}
    directory.mkdir(parents=True, exist_ok=True)
    bound_write(directory / "plan.json", plan)
    print(json.dumps({k: v for k, v in plan.items() if k not in ("jobs", "source_bindings")}))


class Pace:
    def __init__(self):
        self.next_start = 0.0

    def wait(self):
        time.sleep(max(0, self.next_start - time.monotonic()))
        self.next_start = time.monotonic() + 1.0


def checked_rows(result, job):
    start = int(datetime.fromisoformat(job["date"]).replace(tzinfo=UTC).timestamp() * 1000)
    rows = parse_payload(json.dumps(result["values"]).encode(), job["symbol"],
                         start, start + 24 * HOUR - 1)
    lookup = {r["timestamp_ms"]: r for r in rows}
    for stamp, old in job["overlaps"].items():
        if int(stamp) not in lookup or not same_prices(old, lookup[int(stamp)]):
            raise ValueError("Official daily/canonical overlapping mark OHLC conflict")
    return [lookup[t] for t in job["targets"] if t in lookup]


def schema():
    return pa.schema([
        ("instrument_id", pa.string()), ("bar_open_ms", pa.int64()),
        ("bar_open_time", pa.timestamp("ms", tz="UTC")),
        ("bar_close_ms", pa.int64()),
        *[(f, pa.float64()) for f in FIELDS], *[(f"{f}_raw", pa.string()) for f in FIELDS],
        ("source_url", pa.string()), ("source_sha256", pa.string()),
        ("source_retrieved_at", pa.string()), ("source_payload_path", pa.string()),
        ("historical_strategy_eligible", pa.bool_()), ("publication_time_proven", pa.bool_()),
    ])


def validate_overlay(rows, jobs):
    targets = {(j["symbol"], t) for j in jobs for t in j["targets"]}
    start, end = 1609459200000, 1672531200000
    if any(not start <= t < end or t % HOUR for _, t in targets):
        raise ValueError("Targets outside registered development window/hour grid")
    if sum(len(j["targets"]) for j in jobs) != len(targets):
        raise ValueError("Duplicate target keys in plan")
    observed = [(r["instrument_id"], r["bar_open_ms"]) for r in rows]
    if len(observed) != len(set(observed)) or not set(observed) <= targets:
        raise ValueError("Duplicate/unplanned overlay keys")
    for r in rows:
        prices = parse_ohlc([r[f"{f}_raw"] for f in FIELDS])
        if any(not math.isfinite(r[f]) or float(prices[f]) != r[f] for f in FIELDS):
            raise ValueError("Numeric/string OHLC mismatch")
        if r["bar_close_ms"] != r["bar_open_ms"] + HOUR - 1:
            raise ValueError("Wrong overlay close time")
        if r["bar_open_time"] != datetime.fromtimestamp(r["bar_open_ms"] / 1000, UTC):
            raise ValueError("Wrong overlay UTC timestamp")
        if r["historical_strategy_eligible"] or r["publication_time_proven"]:
            raise ValueError("Recovery cannot approve trading/publication vintage")
    return sorted(targets - set(observed))


def recover(directory, cache, export, retry_terminal=False):
    plan_path = directory / "plan.json"
    plan = json.loads(plan_path.read_text())
    jobs = plan["jobs"]
    if len(jobs) > 500:
        raise ValueError("Plan exceeds registered 500 source-day limit")
    contract = {"plan_sha256": sha(plan_path), "script_sha256": sha(Path(__file__)),
                "dependencies": {name: sha(ROOT / "scripts" / name) for name in (
                    "recover_mark_daily.py", "reconcile_mark_gaps.py", "recover_mark_gaps.py",
                    "acquire_usdm_universe.py", "check_universe_feasibility.py")}}
    bound_write(directory / "recovery_contract.json", contract)
    requests, compressed, rows, outcomes, conflicts = 0, 0, [], [], []
    gate = Pace()
    for n, job in enumerate(jobs, 1):
        key = hashlib.sha256(f"{job['symbol']}:{job['date']}".encode()).hexdigest()
        checkpoint = cache / "daily" / key / "result.json"
        prior = json.loads(checkpoint.read_text()) if checkpoint.exists() else None
        terminal = prior and not prior.get("success") and any(
            code in prior.get("error", "") for code in ("404", "403", "418", "429"))
        if terminal and not retry_terminal:
            result = {**prior, "new_requests": 0, "terminal_failure_reused": True}
        else:
            if requests + 2 > 1000:
                raise ValueError("Registered HTTP request budget exceeded")
            result = daily_source(job["symbol"], job["date"], cache, gate,
                                  64 * 1024**2 - compressed)
        if prior and prior.get("success") and not result["success"]:
            raise ValueError("Previously successful source cache failed integrity validation")
        requests += result["new_requests"]
        if result["success"]:
            compressed += result["zip_bytes"]
            try:
                for item in checked_rows(result, job):
                    stamp = item["timestamp_ms"]
                    rows.append({"instrument_id": job["symbol"], "bar_open_ms": stamp,
                                 "bar_open_time": datetime.fromtimestamp(stamp / 1000, UTC),
                                 "bar_close_ms": stamp + HOUR - 1,
                                 **{f: float(item[f]) for f in FIELDS},
                                 **{f"{f}_raw": item[f] for f in FIELDS},
                                 **{k: result[k] for k in (
                                     "source_url", "source_sha256", "source_retrieved_at",
                                     "source_payload_path")},
                                 "historical_strategy_eligible": False,
                                 "publication_time_proven": False})
            except ValueError as exc:
                conflicts.append({"symbol": job["symbol"], "date": job["date"], "error": str(exc)})
        outcomes.append({k: v for k, v in result.items() if k != "values"})
        if not result["success"] and any(c in result.get("error", "") for c in ("403", "418", "429")):
            write(directory / "source_outcomes.json", outcomes)
            raise RuntimeError("HTTP access/rate block: stopped without further requests")
        if n % 10 == 0:
            print(f"recovery {n}/{len(jobs)}; requests={requests}", flush=True)
    write(directory / "source_outcomes.json", outcomes)
    if conflicts:
        write(directory / "conflicts.json", conflicts)
        raise ValueError("Source conflicts prevent overlay export")
    rows.sort(key=lambda r: (r["instrument_id"], r["bar_open_ms"]))
    missing = validate_overlay(rows, jobs)
    table = pa.Table.from_pylist(rows, schema=schema())
    export.mkdir(parents=True, exist_ok=True)
    bound_write(export / "recovery_contract.json", contract)
    path = export / "mark_gap_overlay.parquet"
    temp = export / "mark_gap_overlay.pending.parquet"
    pq.write_table(table, temp, compression="zstd")
    actual = pq.read_table(temp).to_pylist()
    if actual != rows or validate_overlay(actual, jobs) != missing:
        raise ValueError("Parquet roundtrip differs from verified source rows")
    if path.exists():
        if sha(path) != sha(temp):
            raise ValueError("Existing overlay differs: choose a new version")
        temp.unlink()
    else:
        temp.rename(path)
    write(export / "quality_mask.json", {"missing_keys": missing,
                                         "historical_eligible_universe_ready": False})
    summary = {"success": True, "recovery_complete": not missing, "target_hours": plan["target_hours"],
               "recovered_hours": len(rows), "unresolved_hours": len(missing),
               "source_days": len(jobs), "new_http_requests": requests,
               "cached_source_days": sum(bool(o.get("cache_hit")) for o in outcomes),
               "failed_source_days": sum(not o["success"] for o in outcomes),
               "compressed_bytes": compressed, "source_conflicts": 0,
               "overlay_sha256": sha(path), "plan_sha256": sha(plan_path),
               "historical_eligible_universe_ready": False,
               "PnL_computed": False, "OOS_performance_inspected": False}
    write(directory / "summary.json", summary)
    bound_write(export / "manifest.json", {k: v for k, v in summary.items()
                                           if k not in ("new_http_requests", "cached_source_days")})
    print(json.dumps(summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "run"])
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--retry-terminal", action="store_true")
    args = parser.parse_args()
    directory = args.directory or BASE / ("pilot" if args.pilot else "full")
    directory.mkdir(parents=True, exist_ok=True)
    with exclusive_run(directory / ".recovery.lock"):
        if args.command == "plan":
            make_plan(directory, args.pilot)
        else:
            export = DATA / "binance_um_development_mark_recovery" / (
                "v20261121_001_pilot" if args.pilot else "v20261121_001")
            (BASE / "cache").mkdir(parents=True, exist_ok=True)
            with exclusive_run(BASE / "cache/.cache.lock"):
                recover(directory, BASE / "cache", export, args.retry_terminal)


if __name__ == "__main__":
    main()
