"""Normalize acquired observations into a new version; no strategy or OOS decisions."""

from __future__ import annotations

import argparse
import io
import json
import os
import zipfile
from concurrent.futures import as_completed
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
from acquire_usdm_universe import (
    bind_run,
    cancellable_pool,
    digest,
    exclusive_run,
    read_json,
    write_json,
)

BAR_NAMES = [
    "open_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_ms",
    "quote_volume",
    "trade_count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
]
FUND_NAMES = ["event_ms", "funding_interval_hours", "funding_rate"]
HOUR = 3_600_000


def host_path(value: str) -> Path:
    if os.name == "nt" and value.startswith("/") and not value.startswith("//"):
        return Path("\\\\wsl.localhost\\Ubuntu-24.04" + value.replace("/", "\\"))
    return Path(value)


def timestamp(values):
    return pc.cast(pc.cast(values, pa.int64()), pa.timestamp("ms", tz="UTC"))


def parse_csv(body: bytes, filename: str, kind: str) -> pa.Table:
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        members = archive.infolist()
        if (
            len(members) != 1
            or members[0].filename != filename[:-4] + ".csv"
            or members[0].file_size > 10 * 1024**2
        ):
            raise ValueError("unexpected archive members or decompression size")
        raw = archive.read(members[0])
    names = FUND_NAMES if kind == "funding" else BAR_NAMES
    first = raw.split(b"\n", 1)[0].split(b",", 1)[0].decode("utf-8-sig").strip()
    header = first in ("open_time", "calc_time", "funding_time")
    table = pacsv.read_csv(
        pa.BufferReader(raw),
        read_options=pacsv.ReadOptions(
            column_names=names, skip_rows=int(header), use_threads=False
        ),
        convert_options=pacsv.ConvertOptions(
            column_types={name: pa.string() for name in names},
            strings_can_be_null=False,
            null_values=[],
        ),
    )
    if table.num_rows == 0:
        raise ValueError("empty archive")
    return table


def normalize_base(raw: pa.Table, record: dict) -> pa.Table:
    n, kind = raw.num_rows, record["kind"]

    def constant(value, dtype=None):
        return pa.array([value] * n, type=dtype)

    common = {
        "instrument_id": constant(record["symbol"], pa.string()),
        "venue": constant("binance", pa.string()),
        "market": constant("usdm", pa.string()),
        "kind": constant(kind, pa.string()),
        "source_method": constant("official_monthly_archive", pa.string()),
        "source_sha256": constant(record["sha256"], pa.string()),
        "source_url": constant(record["source_url"], pa.string()),
        "source_retrieved_at": constant(record["retrieved_at"], pa.string()),
        "source_recovered": constant(False, pa.bool_()),
        "historical_strategy_eligible": constant(False, pa.bool_()),
    }
    if kind == "funding":
        event = pc.cast(raw["event_ms"], pa.int64())
        rate = pc.cast(raw["funding_rate"], pa.float64())
        if pc.any(pc.invert(pc.is_finite(rate))).as_py():
            raise ValueError("nonfinite funding rate")
        return pa.table(
            {
                **common,
                "event_time": timestamp(event),
                "event_timestamp_ms": event,
                "funding_rate": rate,
                "funding_rate_raw": raw["funding_rate"],
                "funding_interval_hours": pc.cast(raw["funding_interval_hours"], pa.int64()),
                "cashflow_validity": constant("unverified_lifecycle", pa.string()),
            }
        )
    opening, close = pc.cast(raw["open_ms"], pa.int64()), pc.cast(raw["close_ms"], pa.int64())
    if pc.any(pc.not_equal(close, pc.add(opening, HOUR - 1))).as_py():
        raise ValueError("incorrect hourly close timestamps")
    columns = {
        **common,
        "bar_open_time": timestamp(opening),
        "bar_close_time": timestamp(close),
        "bar_open_ms": opening,
        "available_at_lower_bound": timestamp(pc.add(close, 1)),
        "availability_is_lower_bound_only": constant(True, pa.bool_()),
    }
    for field in (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "taker_buy_volume",
        "taker_buy_quote_volume",
    ):
        numeric = pc.cast(raw[field], pa.float64())
        if pc.any(pc.invert(pc.is_finite(numeric))).as_py() or pc.any(pc.less(numeric, 0)).as_py():
            raise ValueError("nonfinite/negative numeric observation")
        if field in ("open", "high", "low", "close") and pc.any(pc.less_equal(numeric, 0)).as_py():
            raise ValueError("nonpositive OHLC")
        columns[field], columns[field + "_raw"] = numeric, raw[field]
    columns["trade_count"] = pc.cast(raw["trade_count"], pa.int64())
    columns["trade_volume_positive"] = (
        pc.greater(columns["volume"], 0) if kind == "trade" else pa.nulls(n, pa.bool_())
    )
    columns["month_constant_zero_trade"] = constant(
        record["quality"]["zero_volume_constant_trade_artifact"], pa.bool_()
    )
    columns["audit_after_known_lifecycle_end"] = pa.nulls(n, pa.bool_())
    columns["audit_after_last_positive_trade"] = pa.nulls(n, pa.bool_())
    return pa.table(columns)


def append_overlay(base: pa.Table, rows: list[dict], record: dict) -> pa.Table:
    if not rows:
        return base
    observed = set(base["bar_open_ms"].to_pylist())
    additions = []
    for source in rows:
        stamp = source["timestamp_ms"]
        if stamp in observed:
            raise ValueError("overlay would overwrite/duplicate an original observation")
        observed.add(stamp)
        row = {name: None for name in base.column_names}
        row.update(
            instrument_id=record["symbol"],
            venue="binance",
            market="usdm",
            kind="mark",
            source_method=source["source_kind"],
            source_sha256=source["source_sha256"],
            source_url=source["source_url"],
            source_retrieved_at=source["source_retrieved_at"],
            source_recovered=True,
            historical_strategy_eligible=False,
            bar_open_ms=stamp,
            bar_open_time=datetime.fromtimestamp(stamp / 1000, UTC),
            bar_close_time=datetime.fromtimestamp((stamp + HOUR - 1) / 1000, UTC),
            available_at_lower_bound=datetime.fromtimestamp((stamp + HOUR) / 1000, UTC),
            availability_is_lower_bound_only=True,
            month_constant_zero_trade=False,
            audit_after_known_lifecycle_end=source["audit_after_known_lifecycle_end"],
            audit_after_last_positive_trade=source["audit_after_last_positive_trade"],
        )
        for field in ("open", "high", "low", "close"):
            row[field], row[field + "_raw"] = float(source[field]), source[field]
        additions.append(row)
    result = pa.concat_tables([base, pa.Table.from_pylist(additions, schema=base.schema)])
    return result.take(pc.sort_indices(result, sort_keys=[("bar_open_ms", "ascending")]))


def normalize_partition(item: dict, args: argparse.Namespace, overlay: dict) -> dict:
    key = item["key"]
    identity = digest(key.encode())
    report = read_json(args.download_dir / "files" / (identity + ".json"))
    if any(report[field] != item[field] for field in ("key", "symbol", "kind", "month")):
        raise ValueError("plan/report mismatch")
    source = host_path(report["path"])
    if not source.resolve().is_relative_to((args.data_root / "raw").resolve()):
        raise ValueError("raw source outside shared root")
    body = source.read_bytes()
    if digest(body) != report["sha256"] or len(body) != item["size"]:
        raise ValueError("raw source hash/size changed")
    relative = f"{item['kind']}/{item['symbol']}/{item['month']}.parquet"
    destination = args.output_dir / "observations" / relative
    entry = args.output_dir / "index" / (identity + ".json")
    if entry.exists():
        previous = read_json(entry)
        if (
            previous["raw_sha256"] != report["sha256"]
            or digest(destination.read_bytes()) != previous["parquet_sha256"]
        ):
            raise ValueError("normalized partition provenance/integrity failure")
        return {**previous, "cache_hit": True}
    if destination.exists():
        raise ValueError("unmanifested partition exists; investigate rather than overwrite")
    table = normalize_base(parse_csv(body, source.name, item["kind"]), report)
    added = overlay.get((item["symbol"], item["month"]), []) if item["kind"] == "mark" else []
    table = append_overlay(table, added, report)
    expected = report["quality"]["row_count"] + len(added)
    time_column = "event_timestamp_ms" if item["kind"] == "funding" else "bar_open_ms"
    if table.num_rows != expected or len(set(table[time_column].to_pylist())) != expected:
        raise ValueError("row count or key uniqueness mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".parquet.part")
    pq.write_table(table, temporary, compression="zstd")
    with pa.OSFile(str(temporary), "rb") as handle:
        restored = pq.read_table(handle, use_threads=False)
    if not table.equals(restored):
        raise ValueError("normalized Parquet roundtrip mismatch")
    temporary.replace(destination)
    result = {
        "symbol": item["symbol"],
        "kind": item["kind"],
        "month": item["month"],
        "relative_path": "observations/" + relative,
        "raw_sha256": report["sha256"],
        "parquet_sha256": digest(destination.read_bytes()),
        "rows": table.num_rows,
        "overlay_rows": len(added),
        "cache_hit": False,
        "first_time_ms": pc.min(table[time_column]).as_py(),
        "last_time_ms": pc.max(table[time_column]).as_py(),
    }
    write_json(entry, result)
    return result


def run(args: argparse.Namespace) -> bool:
    plan_body = (args.census_dir / "download_plan.json").read_bytes()
    plan = json.loads(plan_body)
    manifest = read_json(args.overlay_dir / "manifest.json")
    parquet = args.overlay_dir / "mark_gap_overlay.parquet"
    if digest(parquet.read_bytes()) != manifest["parquet_sha256"]:
        raise ValueError("overlay integrity failure")
    lifecycle = read_json(args.lifecycle_dir / "summary.json")
    if not lifecycle["success"]:
        raise ValueError("lifecycle review build has errors")
    for name, field in (("identity_ledger", "ledger_sha256"), ("events", "events_sha256")):
        if digest((args.lifecycle_dir / (name + ".json")).read_bytes()) != lifecycle[field]:
            raise ValueError("lifecycle review integrity failure")
    overlay = {}
    for row in pq.read_table(parquet).to_pylist():
        source = {
            **row,
            **{field: row[field + "_raw"] for field in ("open", "high", "low", "close")},
        }
        label = datetime.fromtimestamp(row["timestamp_ms"] / 1000, UTC).strftime("%Y-%m")
        overlay.setdefault((row["symbol"], label), []).append(source)
    files = plan["files"]
    if args.symbols:
        selected = set(args.symbols.split(","))
        if not selected <= {r["symbol"] for r in files}:
            raise ValueError("unknown selected symbol")
        files = [r for r in files if r["symbol"] in selected]
    if args.months:
        files = [r for r in files if r["month"] in args.months.split(",")]
    selected_mark = {(r["symbol"], r["month"]) for r in files if r["kind"] == "mark"}
    expected_overlay = sum(len(rows) for key, rows in overlay.items() if key in selected_mark)
    if not args.symbols and not args.months and not set(overlay) <= selected_mark:
        raise ValueError("overlay keys have no base partition")
    if not files:
        raise ValueError("empty normalization selection")
    bind_run(
        args.output_dir,
        {
            "schema": 1,
            "lifecycle_ledger_sha256": lifecycle["ledger_sha256"],
            "lifecycle_events_sha256": lifecycle["events_sha256"],
            "plan_sha256": digest(plan_body),
            "overlay_sha256": manifest["parquet_sha256"],
            "tool_sha256": digest(Path(__file__).read_bytes()),
            "symbols": args.symbols,
            "months": args.months,
        },
    )
    for name in ("identity_ledger", "events", "summary"):
        write_json(
            args.output_dir / "lifecycle" / (name + ".json"),
            read_json(args.lifecycle_dir / (name + ".json")),
        )
    results, errors = [], []
    with cancellable_pool(args.workers) as pool:
        pending = {pool.submit(normalize_partition, item, args, overlay): item for item in files}
        for index, future in enumerate(as_completed(pending), 1):
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append({"key": pending[future]["key"], "error": str(exc)})
            if index % 2000 == 0 or index == len(files):
                print(f"normalize {index}/{len(files)}; failed={len(errors)}", flush=True)
    actual_overlay = sum(r["overlay_rows"] for r in results)
    if actual_overlay != expected_overlay:
        errors.append(
            {
                "error": "overlay union mismatch",
                "expected": expected_overlay,
                "actual": actual_overlay,
            }
        )
    summary = {
        "success": not errors and len(results) == len(files),
        "full_scope": not args.symbols and not args.months,
        "planned_partitions": len(files),
        "verified_partitions": len(results),
        "rows_by_kind": {
            kind: sum(r["rows"] for r in results if r["kind"] == kind)
            for kind in ("trade", "mark", "funding")
        },
        "overlay_rows_integrated": actual_overlay,
        "overlay_rows_expected": expected_overlay,
        "cache_hits": sum(r["cache_hit"] for r in results),
        "errors": errors,
        "historical_eligible_universe_ready": False,
        "strategy_and_OOS_decisions": "deferred_by_user",
    }
    write_json(
        args.output_dir / "manifest.json",
        {
            **summary,
            "inputs": read_json(args.output_dir / "run_config.json"),
            "schema_notes": "UTC ms; close+1ms is availability lower bound only; funding is observed, not proven paid",
        },
    )
    write_json(
        args.output_dir / "quality/mark_unresolved.json",
        read_json(args.overlay_dir / "quality_mask.json"),
    )
    write_json(
        args.output_dir / "quality/source_interior_gaps.json",
        read_json(args.audit_dir / "interior_gaps.json"),
    )
    write_json(
        args.output_dir / "quality/source_month_gaps.json",
        read_json(args.audit_dir / "review_rollup.json")["whole_month_interior_gaps"],
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary["success"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "data-root",
        "census-dir",
        "download-dir",
        "overlay-dir",
        "audit-dir",
        "lifecycle-dir",
        "output-dir",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--symbols")
    parser.add_argument("--months")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()
    with exclusive_run(args.output_dir / ".build.lock"):
        raise SystemExit(0 if run(args) else 1)
