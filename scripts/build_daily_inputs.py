"""Build immutable daily technical-input sidecars; strategy/OOS choices stay deferred."""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from build_research_data import normalize_base, parse_csv
from collect_cmc_weekly import LogTee, checked_source
from daily_input_rules import DAY, REASONS, make_daily, merge_hour, ms, size_schedule
from screen_full_universe import load_inputs

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parents[1] / "data"
SOURCE = SHARED / "canonical/binance_um_research/v20261117_001"
DOWNLOAD_REPORTS = ROOT / "data/interim/usdm_universe/download_full_20261117/files"
FULL = SHARED / "canonical/binance_um_daily_research/v20261118_001"
PILOT = ROOT / "data/interim/daily_research_pilot_20261118"
PILOT_WINDOWS = {
    "BTCUSDT": ("2023-01-01", "2023-06-01"),
    "BNXUSDT": ("2023-01-01", "2023-07-01"),
    "PUMPUSDT": ("2025-04-01", "2025-09-01"),
    "LITUSDT": ("2025-12-01", "2026-04-01"),
    "SUNUSDT": ("2024-08-01", "2025-01-01"),
}
COUNTS = (
    "price_funding_data_candidate",
    "four_factor_assumed_size_candidate",
    "four_factor_class_review_clear_candidate",
    "strict_four_factor_eligible",
)
BAR_FIELDS = ["bar_open_ms", "close", "close_raw", "source_recovered"]
TRADE_FIELDS = BAR_FIELDS + [
    "volume",
    "quote_volume",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "trade_count",
]
FUND_FIELDS = ["event_timestamp_ms", "funding_rate", "funding_rate_raw", "funding_interval_hours"]
STRING_FIELDS = {
    "instrument_id",
    "data_day",
    "trade_close_raw",
    "funding_rate_raw",
    "mapping_status",
    "size_snapshot_date",
    "size_market_cap_decimal",
}
FLOAT_FIELDS = {
    "trade_close",
    "mark_close",
    "trade_volume_sum",
    "trade_quote_volume_sum",
    "taker_buy_quote_volume_sum",
    "funding_rate_observed",
}
INT_FIELDS = {
    "reference_time_ms",
    "episode_number",
    "close_episode_number",
    "trade_hours",
    "mark_hours",
    "recovered_mark_hours",
    "consecutive_daily_closes",
    "funding_event_ms",
    "funding_interval_hours",
    "funding_age_ms",
    "vendor_asset_id",
    "size_assumed_available_ms",
    "size_assumed_expires_ms",
    "base_failure_mask",
    "four_factor_failure_mask",
}


def midnight(text):
    return ms(text + "T00:00:00+00:00")


def table_for(rows):
    fields = [
        (
            key,
            pa.string()
            if key in STRING_FIELDS
            else pa.float64()
            if key in FLOAT_FIELDS
            else pa.int64()
            if key in INT_FIELDS
            else pa.bool_(),
        )
        for key in rows[0]
    ]
    return pa.Table.from_pylist(rows, schema=pa.schema(fields))


def load_context():
    data = load_inputs()
    events_path = ROOT / "data/interim/usdm_universe/lifecycle_review_20261118/events.json"
    if digest(events_path.read_bytes()) != data["lifecycle_summary"]["events_sha256"]:
        raise ValueError("event ledger integrity failure")
    cmc = ROOT / "data/interim/cmc_weekly_20261118"
    cmc_summary = read_json(cmc / "full/summary.json")
    if not cmc_summary["success"] or not cmc_summary["full_scope"] or cmc_summary["errors"]:
        raise ValueError("CMC acquisition incomplete")
    audit_root = ROOT / "data/interim/cmc_identity_audit_002_20261118"
    audit_summary = read_json(audit_root / "summary.json")
    audit_binding = read_json(audit_root / "run_config.json")
    if (
        digest((audit_root / "summary.json").read_bytes())
        != data["prior_review"]["inputs"]["audit_summary_sha256"]
        or audit_summary["inputs"] != audit_binding
    ):
        raise ValueError("CMC independent audit binding mismatch")
    if (
        digest((cmc / "full/summary.json").read_bytes())
        != audit_binding["acquisition_summary_sha256"]
        or digest((cmc / "full/date_coverage.json").read_bytes())
        != audit_binding["date_coverage_sha256"]
    ):
        raise ValueError("CMC frozen acquisition/date coverage mismatch")
    date_indexes = {r["date"]: r for r in read_json(cmc / "full/date_coverage.json")}
    rows, cmc_hashes = [], {}
    for label in cmc_summary["inputs"]["selected_dates"]:
        path = cmc / "full/partitions" / (label + ".json")
        body = path.read_bytes()
        index = read_json(cmc / "full/index" / (label + ".json"))
        if index != date_indexes[label]:
            raise ValueError("CMC frozen index mismatch")
        if digest(body) != index["parsed_sha256"]:
            raise ValueError("CMC partition integrity failure")
        parsed = json.loads(body)
        if len(parsed) != index["rows"] or any(r["snapshot_date"] != label for r in parsed):
            raise ValueError("CMC count/date mismatch")
        rows.extend(parsed)
        cmc_hashes[label] = digest(body)
    if len(rows) != cmc_summary["rows"]:
        raise ValueError("CMC total count mismatch")
    data["schedules"] = size_schedule(rows)
    data["files_by_symbol"] = defaultdict(list)
    for item in data["plan"]["files"]:
        data["files_by_symbol"][item["symbol"]].append(item)
    data["ledger_by_id"] = {r["instrument_id"]: r for r in data["ledger"]}
    data["queue_by_id"] = {r["instrument_id"]: r for r in data["cmc_queue"]}
    dependencies = (
        "daily_input_rules.py",
        "build_research_data.py",
        "screen_full_universe.py",
        "acquire_usdm_universe.py",
    )
    data["binding"] = {
        "tool_sha256": digest(Path(__file__).read_bytes()),
        "source_metadata_hashes": data["hashes"],
        "dependency_hashes": {
            name: digest((ROOT / "scripts" / name).read_bytes()) for name in dependencies
        },
        "event_sha256": digest(events_path.read_bytes()),
        "cmc_partition_hashes": cmc_hashes,
        "size_assumption": {
            "lag_days_after_snapshot_day_end": 7,
            "valid_days": 7,
            "vintage_proven": False,
        },
        "decision_clock": "next UTC midnight lower bound only; not an execution schedule",
        "OOS_and_strategy_decisions": "deferred_by_user",
    }
    return data


def read_partition(item, decode=True):
    index_path = SOURCE / "index" / (digest(item["key"].encode()) + ".json")
    index_body = index_path.read_bytes()
    index = json.loads(index_body)
    report_body = (DOWNLOAD_REPORTS / (digest(item["key"].encode()) + ".json")).read_bytes()
    report = json.loads(report_body)
    if (
        any(report[k] != item[k] for k in ("key", "symbol", "kind", "month"))
        or report["bytes"] != item["size"]
    ):
        raise ValueError("acquisition report/plan mismatch")
    if (
        index["raw_sha256"] != report["sha256"]
        or index["rows"] != report["quality"]["row_count"] + index["overlay_rows"]
    ):
        raise ValueError("normalized/acquisition provenance mismatch")
    relative = f"observations/{item['kind']}/{item['symbol']}/{item['month']}.parquet"
    if index["relative_path"] != relative or any(
        index[k] != item[k] for k in ("symbol", "kind", "month")
    ):
        raise ValueError("normalized index identity/path mismatch")
    body = (SOURCE / relative).read_bytes()
    if digest(body) != index["parquet_sha256"]:
        raise ValueError("Parquet integrity failure: " + relative)
    binding = {
        "index_sha256": digest(index_body),
        "parquet_sha256": digest(body),
        "raw_sha256": index["raw_sha256"],
        "acquisition_report_sha256": digest(report_body),
    }
    if not decode:
        return None, binding
    fields = (
        FUND_FIELDS
        if item["kind"] == "funding"
        else TRADE_FIELDS
        if item["kind"] == "trade"
        else BAR_FIELDS
    )
    table = pq.read_table(pa.BufferReader(body), columns=fields, use_threads=False)
    if table.num_rows != index["rows"]:
        raise ValueError("Parquet row count mismatch")
    return table.to_pylist(), binding


def legacy_rows():
    directory = ROOT / "data/interim/identity_followup_20261118"
    config = read_json(ROOT / "config/identity_followup_sources_20261118.json")
    urls = {r["id"]: r["url"] for r in config["sources"]}
    body, meta, _ = checked_source(directory, "bnx_legacy_feb_zip", urls["bnx_legacy_feb_zip"])
    checksum, _, _ = checked_source(
        directory, "bnx_legacy_feb_checksum", urls["bnx_legacy_feb_checksum"]
    )
    name = "BNXUSDTSETTLED-1h-2023-02.zip"
    if checksum.decode().split() != [digest(body), name]:
        raise ValueError("BNX legacy checksum failure")
    raw = parse_csv(body, name, "trade")
    record = {
        "kind": "trade",
        "symbol": "BNXUSDT",
        "sha256": digest(body),
        "source_url": meta["url"],
        "retrieved_at": meta["retrieved_at"],
        "quality": {"zero_volume_constant_trade_artifact": False},
    }
    table = normalize_base(raw, record).select(TRADE_FIELDS)
    limit = ms("2023-02-11T04:00:00+00:00")
    rows = [r for r in table.to_pylist() if r["bar_open_ms"] < limit]
    if len(rows) != 244:
        raise ValueError("BNX legacy pre-close hour count mismatch")
    for row in rows:
        row["source_recovered"] = True
    return rows, {
        "sha256": digest(body),
        "source_url": meta["url"],
        "pre_close_hours": len(rows),
        "post_close_rows_not_integrated": table.num_rows - len(rows),
    }


def build_symbol(symbol, window, data, output):
    start, end = map(midnight, window)
    context_start = max(midnight("2021-01-01"), start - 120 * DAY)
    first_month = datetime.fromtimestamp(context_start / 1000, UTC).strftime("%Y-%m")
    last_month = datetime.fromtimestamp((end - 1) / 1000, UTC).strftime("%Y-%m")
    items = [
        r
        for r in data["files_by_symbol"].get(symbol, [])
        if first_month <= r["month"] <= last_month
    ]
    target, index_path = (
        output / "daily" / (symbol + ".parquet"),
        output / "index" / (symbol + ".json"),
    )
    cached = index_path.exists()
    previous = read_json(index_path) if cached else None
    if cached and digest(target.read_bytes()) != previous["daily_sha256"]:
        raise ValueError("daily checkpoint integrity failure")
    if not cached and target.exists():
        raise ValueError("unmanifested daily output; inspect before retry")
    trade, mark, funding, source_bindings = {}, {}, {}, {}
    for item in items:
        rows, binding = read_partition(item, decode=not cached)
        source_bindings[item["key"]] = binding
        if cached:
            continue
        for row in rows:
            if item["kind"] == "funding":
                stamp = row["event_timestamp_ms"]
                if stamp in funding and funding[stamp] != row:
                    raise ValueError("conflicting funding duplicate")
                funding[stamp] = row
            else:
                merge_hour(trade if item["kind"] == "trade" else mark, row)
    legacy, legacy_binding = data["legacy"] if symbol == "BNXUSDT" else ([], None)
    used_legacy = [r for r in legacy if context_start <= r["bar_open_ms"] < end]
    satisfied = len(used_legacy) == 244
    if cached:
        if (
            previous["sources"] != source_bindings
            or previous["legacy"] != legacy_binding
            or previous["window"] != list(window)
        ):
            raise ValueError("daily checkpoint source/config changed")
        return previous, True
    for row in used_legacy:
        merge_hour(trade, row)
    rows = make_daily(
        symbol,
        context_start,
        end,
        trade,
        mark,
        list(funding.values()),
        data["ledger_by_id"][symbol],
        data["queue_by_id"][symbol],
        data["episode_facts"],
        data["policy"],
        data["schedules"],
        satisfied,
    )
    rows = [r for r in rows if start <= r["reference_time_ms"] - DAY < end]
    table = table_for(rows)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".parquet.part")
    pq.write_table(table, temporary, compression="zstd")
    restored = pq.read_table(pa.BufferReader(temporary.read_bytes()), use_threads=False)
    if not table.equals(restored):
        raise ValueError("daily Parquet roundtrip mismatch")
    temporary.replace(target)
    counts = {key: sum(r[key] for r in rows) for key in COUNTS}
    result = {
        "instrument_id": symbol,
        "window": list(window),
        "rows": len(rows),
        "source_partitions": len(items),
        "sources": source_bindings,
        "legacy": legacy_binding,
        "legacy_hours_consumed": len(used_legacy),
        "legacy_condition_satisfied": satisfied,
        "counts": counts,
        "daily_sha256": digest(target.read_bytes()),
        "historical_strategy_eligible": False,
    }
    write_json(index_path, result)
    return result, False


def summarize(output, results, full_scope, elapsed, hits):
    daily, failure_counts, distinct = {}, Counter(), {key: 0 for key in COUNTS}
    for result in results:
        table = pq.read_table(
            pa.BufferReader(
                (output / "daily" / (result["instrument_id"] + ".parquet")).read_bytes()
            ),
            columns=[
                "data_day",
                "reference_time_ms",
                "base_failure_mask",
                "four_factor_failure_mask",
                *COUNTS,
            ],
            use_threads=False,
        )
        for key in COUNTS:
            distinct[key] += int(result["counts"][key] > 0)
        for row in table.to_pylist():
            day = daily.setdefault(
                row["data_day"],
                {
                    "data_day": row["data_day"],
                    "reference_time_ms": row["reference_time_ms"],
                    **{key: 0 for key in COUNTS},
                },
            )
            for key in COUNTS:
                day[key] += int(row[key])
            for reason, bit in REASONS.items():
                if row["four_factor_failure_mask"] & bit:
                    failure_counts[reason] += 1
    write_json(output / "daily_counts.json", [daily[key] for key in sorted(daily)])
    write_json(output / "reason_counts.json", dict(failure_counts))
    result = {
        "success": True,
        "errors": [],
        "full_scope": full_scope,
        "identifiers": len(results),
        "daily_rows": sum(r["rows"] for r in results),
        "source_partitions_verified": sum(r["source_partitions"] for r in results),
        "legacy_BNX_hours_consumed": sum(r["legacy_hours_consumed"] for r in results),
        "identifiers_ever_passing_diagnostic": distinct,
        "cache_hits": hits,
        "elapsed_seconds": round(elapsed, 3),
        "historical_eligible_universe_ready": False,
        "strict_Size_publication_vintage_proven": False,
        "strategy_and_OOS_decisions": "deferred_by_user",
        "OOS_performance_inspected": False,
    }
    write_json(output / "manifest.json", result)
    print(json.dumps(result, sort_keys=True))


def run(args):
    output = args.output or (PILOT if args.action == "pilot" else FULL)
    if args.action == "summary":
        for directory in (PILOT, FULL) if args.output is None else (args.output,):
            path = directory / "manifest.json"
            print(
                json.dumps({"path": str(path), **read_json(path)}, sort_keys=True)
                if path.exists()
                else str(path) + ": not run"
            )
        return
    started = time.monotonic()
    data = load_context()
    data["legacy"] = legacy_rows()
    windows = (
        {symbol: list(window) for symbol, window in PILOT_WINDOWS.items()}
        if args.action == "pilot"
        else {symbol: ["2021-01-01", "2026-11-01"] for symbol in sorted(data["ledger_by_id"])}
    )
    binding = {
        **data["binding"],
        "windows": windows,
        "legacy": data["legacy"][1],
        "reason_bits": REASONS,
    }
    output.mkdir(parents=True, exist_ok=True)
    with exclusive_run(output / ".daily.lock"):
        bind_run(output, binding)
        results, hits = [], 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = [
                pool.submit(build_symbol, symbol, window, data, output)
                for symbol, window in windows.items()
            ]
            try:
                for number, job in enumerate(as_completed(jobs), 1):
                    result, cached = job.result()
                    results.append(result)
                    hits += int(cached)
                    if number % 10 == 0 or number == len(jobs):
                        print(f"daily inputs {number}/{len(jobs)}; cache_hits={hits}", flush=True)
            except BaseException:
                for job in jobs:
                    job.cancel()
                raise
        summarize(output, results, args.action == "full", time.monotonic() - started, hits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["pilot", "full", "summary"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error("workers must be1..4")
    log = ROOT / "reports/acquisition" / f"daily_inputs_{args.action}_20261118.log"
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
