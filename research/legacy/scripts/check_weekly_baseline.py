"""Integrity-checked development weekly coverage; never read price/target columns."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from collect_cmc_weekly import LogTee
from weekly_contract import COUNTS, millis, utc, validate_contract, weekly_calendar, weekly_flags

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1] / "data/canonical/binance_um_daily_research/v20261118_001"
OUTPUT = ROOT / "data/interim/weekly_baseline_stage0_20261118"
CONFIG = ROOT / "config/weekly_baseline_v1.json"
COLUMNS = ["instrument_id", "data_day", "reference_time_ms", *COUNTS]


def source_indices(source: Path) -> tuple[dict, dict]:
    manifest_body = (source / "manifest.json").read_bytes()
    manifest = json.loads(manifest_body)
    if not manifest["success"] or manifest["errors"] or not manifest["full_scope"]:
        raise ValueError("require successful full daily release")
    run_body = (source / "run_config.json").read_bytes()
    run = json.loads(run_body)
    names = sorted(run["windows"])
    if len(names) != manifest["identifiers"] or len(names) != 924:
        raise ValueError("daily identifier population mismatch")
    indices, hashes = {}, {}
    for symbol in names:
        if not symbol.isalnum() or not symbol.endswith("USDT"):
            raise ValueError("unsafe identifier")
        body = (source / "index" / (symbol + ".json")).read_bytes()
        item = json.loads(body)
        if item["instrument_id"] != symbol or item["window"] != run["windows"][symbol]:
            raise ValueError("daily index identity/window mismatch")
        if item["window"] != ["2021-01-01", "2026-11-01"] or item["rows"] != 2130:
            raise ValueError("unexpected daily window/row count")
        indices[symbol] = item
        hashes[symbol] = digest(body)
    if sum(item["rows"] for item in indices.values()) != manifest["daily_rows"]:
        raise ValueError("daily manifest row count mismatch")
    return indices, {
        "source_manifest_sha256": digest(manifest_body),
        "source_run_config_sha256": digest(run_body),
        "source_index_hashes": hashes,
    }


def projected_rows(body: bytes, symbol: str, index: dict, config: dict) -> list[dict]:
    if digest(body) != index["daily_sha256"]:
        raise ValueError("daily Parquet integrity failure: " + symbol)
    if pq.ParquetFile(pa.BufferReader(body)).metadata.num_rows != index["rows"]:
        raise ValueError("daily Parquet row count mismatch")
    table = pq.read_table(
        pa.BufferReader(body),
        columns=COLUMNS,
        filters=[
            ("reference_time_ms", ">=", millis(utc(config["development_start"]))),
            ("reference_time_ms", "<", millis(utc(config["sealed_oos_start"]))),
        ],
        use_threads=False,
    )
    rows = table.to_pylist()
    if any(row["instrument_id"] != symbol for row in rows):
        raise ValueError("daily row identity mismatch")
    expected = (utc(config["sealed_oos_start"]) - utc(config["development_start"])).days - 1
    # The source begins with Jan1 data (Jan2 reference); Jan1 reference is absent.
    refs = [row["reference_time_ms"] for row in rows]
    first = millis(utc(config["development_start"])) + 86400000
    if len(refs) != expected or sorted(refs) != list(
        range(first, first + expected * 86400000, 86400000)
    ):
        raise ValueError("development daily references incomplete or duplicated")
    return rows


def check_symbol(source, output, symbol, index, config, calendar):
    # Hash complete files for integrity, but materialize only development flags.
    body = (source / "daily" / (symbol + ".parquet")).read_bytes()
    rows = projected_rows(body, symbol, index, config)
    values = weekly_flags(rows, calendar, config)
    target = output / "instruments" / (symbol + ".json")
    expected = {"instrument_id": symbol, "daily_sha256": index["daily_sha256"], "weekly": values}
    if target.exists():
        if read_json(target) != expected:
            raise ValueError("checkpoint content conflict: " + symbol)
        return values, True
    write_json(target, expected)
    return values, False


def run(args):
    output = args.output or OUTPUT / args.action
    if args.action == "summary":
        for folder in (OUTPUT / "pilot", OUTPUT / "full") if args.output is None else (output,):
            path = folder / "summary.json"
            print(
                json.dumps({"path": str(path), **read_json(path)})
                if path.exists()
                else f"{path}: not run"
            )
        return
    started = time.monotonic()
    config_body = CONFIG.read_bytes()
    config = json.loads(config_body)
    validate_contract(config)
    calendar = weekly_calendar(config)
    indices, source_binding = source_indices(args.source)
    names = ["BTCUSDT", "BNXUSDT", "SUNUSDT"] if args.action == "pilot" else sorted(indices)
    binding = {
        **source_binding,
        "config_sha256": digest(config_body),
        "script_sha256": digest(Path(__file__).read_bytes()),
        "helper_sha256": digest((ROOT / "scripts/weekly_contract.py").read_bytes()),
        "shared_helper_hashes": {
            name: digest((ROOT / "scripts" / name).read_bytes())
            for name in ("acquire_usdm_universe.py", "collect_cmc_weekly.py")
        },
        "identifiers": names,
        "projected_columns": COLUMNS,
        "OOS_performance_inspected": False,
    }
    with exclusive_run(output / ".weekly.lock"):
        bind_run(output, binding)
        write_json(output / "calendar.json", calendar)
        weekly = [
            {"decision_date": row["decision_date"], **{key: 0 for key in COUNTS}}
            for row in calendar
        ]
        hits = 0
        for number, symbol in enumerate(names, 1):
            values, cached = check_symbol(
                args.source, output, symbol, indices[symbol], config, calendar
            )
            hits += int(cached)
            for total, flags in zip(weekly, values, strict=True):
                if total["decision_date"] != flags["decision_date"]:
                    raise ValueError("checkpoint weekly calendar mismatch")
                for key in COUNTS:
                    total[key] += int(flags[key])
            if number % 100 == 0 or number == len(names):
                print(f"weekly coverage {number}/{len(names)}; cache_hits={hits}", flush=True)
        threshold = config["coverage_diagnostic_minimum_names"]
        for row in weekly:
            row["assumed_size_at_least_20_names"] = (
                row["four_factor_assumed_size_candidate"] >= threshold
            )
        stats = {}
        for period in ("all_development", "2021", "2022", "2023", "2024"):
            subset = [
                r
                for r in weekly
                if period == "all_development" or r["decision_date"].startswith(period)
            ]
            stats[period] = {
                "decisions": len(subset),
                "assumed_size_fraction_at_least_20_names": sum(
                    r["assumed_size_at_least_20_names"] for r in subset
                )
                / len(subset),
                "counts": {
                    key: {
                        "minimum": min(r[key] for r in subset),
                        "median": statistics.median(r[key] for r in subset),
                        "maximum": max(r[key] for r in subset),
                    }
                    for key in COUNTS
                },
            }
        permissions = {
            f"{split['name']}_{purpose}": {
                status: sum(r[f"{split['name']}_{purpose}"] == status for r in calendar)
                for status in ("usable_by_time_only", "purged_label_boundary", "outside_window")
            }
            for split in config["rounds"]
            for purpose in ("train", "validation")
        }
        write_json(output / "weekly_counts.json", weekly)
        write_json(output / "coverage_by_year.json", stats)
        result = {
            "success": True,
            "errors": [],
            "full_scope": args.action == "full",
            "identifiers": len(names),
            "weekly_decisions": len(calendar),
            "cache_hits": hits,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "split_calendar_permissions": permissions,
            "development_assumed_size_counts": stats["all_development"]["counts"][
                "four_factor_assumed_size_candidate"
            ],
            "development_assumed_size_fraction_at_least_20_names": stats["all_development"][
                "assumed_size_fraction_at_least_20_names"
            ],
            "historical_eligible_universe_ready": False,
            "strict_Size_publication_vintage_proven": False,
            "label_values_computed": False,
            "model_fitted": False,
            "PnL_computed": False,
            "OOS_performance_inspected": False,
            "execution_and_label_availability": "unverified_research_assumptions",
        }
        write_json(output / "summary.json", result)
        print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pilot", "full", "summary"))
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    log = ROOT / "reports/acquisition" / f"weekly_baseline_{args.action}_20261118.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    print("Log: " + str(log), flush=True)
    with (
        log.open("a", encoding="utf-8") as handle,
        redirect_stdout(LogTee(sys.stdout, handle)),
        redirect_stderr(LogTee(sys.stderr, handle)),
    ):
        try:
            run(args)
        except Exception:
            traceback.print_exc()
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
