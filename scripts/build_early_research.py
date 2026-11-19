"""Build a separate2020 observation release and daily long panel; no factor/PnL work."""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from audit_history_extension import DATA, SOURCE, check_file, resolve_raw
from build_research_data import normalize_base, parse_csv
from check_early_cases import END as API_END
from check_early_cases import overlap_check, parse_funding, stamp, verified_article
from collect_cmc_weekly import LogTee, checked_source
from early_research_rules import add_flags, api_table, daily_rows, daily_table

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "data/interim/usdm_universe/early_cases_20261119"
FULL = DATA / "canonical/binance_um_early_research/v20261119_001"
PILOT = ROOT / "data/interim/early_research_pilot_20261119"
SYMBOLS = {"BTCUSDT", "ETHUSDT", "QTUMUSDT", "DEFIUSDT", "LENDUSDT", "AAVEUSDT"}
BAR_FIELDS = [
    "bar_open_ms",
    "close",
    "close_raw",
    "volume",
    "quote_volume",
    "taker_buy_quote_volume",
]
FUND_FIELDS = [
    "event_timestamp_ms",
    "funding_rate_raw",
    "funding_interval_hours",
    "quarantine_from_trading_reconstruction",
]


def load_inputs():
    paths = {
        "plan": SOURCE / "inventory/download_plan.json",
        "inventory": SOURCE / "inventory/summary.json",
        "download": SOURCE / "download/summary.json",
        "audit": ROOT / "data/interim/usdm_universe/early_history_audit_20261119/full/summary.json",
        "cases_summary": CASES / "review_002/summary.json",
        "cases_binding": CASES / "review_002/run_config.json",
        "case_observations": CASES / "review_002/qtum_february_observations.json",
        "case_facts": CASES / "review_002/facts.json",
        "case_decisions": CASES / "review_002/decisions.json",
        "case_config": ROOT / "config/early_cases_20261119.json",
        "population": ROOT / "data/interim/usdm_universe/census_full_20261117/run_config.json",
    }
    bodies = {key: path.read_bytes() for key, path in paths.items()}
    inputs = {key: json.loads(body) for key, body in bodies.items()}
    plan, download, audit = inputs["plan"], inputs["download"], inputs["audit"]
    if (
        not download["success"]
        or download["errors"]
        or not audit["success"]
        or audit["errors"]
        or inputs["inventory"]["plan_hashes"]["download_plan.json"] != digest(bodies["plan"])
        or len(plan["files"]) != 1526
        or sum(r["size"] for r in plan["files"]) != 24153565
        or audit["verified_raw_files"] != 1526
        or audit["funding_rows"] != 43027
        or download["verified_files"] != 1526
        or download["verified_bytes"] != 24153565
    ):
        raise ValueError("early source corpus is incomplete or changed")
    if any(not "2020-01" <= r["month"] <= "2020-12" for r in plan["files"]):
        raise ValueError("this release is2020 only;no partial2019 insertion")
    if len({r["key"] for r in plan["files"]}) != len(plan["files"]):
        raise ValueError("duplicate planned source partition")
    case = inputs["cases_summary"]
    if (
        case["issues"] != ["qtum_launch: exact dated clause not locally verified"]
        or case["success"] is not False
        or not case["march_overlap_rate_matches"]
    ):
        raise ValueError("unexpected case gate;do not silently waive failures")
    binding = inputs["cases_binding"]
    if binding["config_sha256"] != digest(bodies["case_config"]):
        raise ValueError("case configuration mismatch")
    if binding["script_sha256"] != digest((ROOT / "scripts/check_early_cases.py").read_bytes()):
        raise ValueError("case review tool changed")
    for name, sha in binding["dependencies"].items():
        if digest((ROOT / "scripts" / name).read_bytes()) != sha:
            raise ValueError("case review dependency changed")
    sources = {}
    for spec in inputs["case_config"]["sources"]:
        if spec["id"] not in binding["captured_source_hashes"]:
            continue
        body, metadata, _ = checked_source(CASES, spec["id"], spec["url"])
        if metadata["sha256"] != binding["captured_source_hashes"][spec["id"]]:
            raise ValueError("case source SHA mismatch")
        sources[spec["id"]] = (body, metadata)
    for label, code, fragments in (
        (
            "defi_launch",
            "ebee6da5df3946519fdb9ab27706d1a4",
            ["2020/08/28 7:00 AM (UTC)", "not the ticker of a separate token"],
        ),
        (
            "lend_settlement",
            "17595222999545348c8acdd5dc41c00a",
            [
                "2020/10/10 0:00 AM (UTC)",
                "settling all LEND/USDT perpetual contract positions",
                "2020/10/16 7:00 AM (UTC)",
            ],
        ),
    ):
        fact, _ = verified_article(sources[label][0], code, fragments)
        if not fact["clauses_verified"] or not inputs["case_facts"][label]["clauses_verified"]:
            raise ValueError("known lifecycle clauses not verified")
    api_rows = parse_funding(json.loads(sources["qtum_funding"][0]))
    february = [r for r in api_rows if r["event_timestamp_ms"] < API_END]
    saved = inputs["case_observations"]
    if (
        len(february) != 31
        or len(saved) != 31
        or any(any(a[key] != b[key] for key in a) for a, b in zip(february, saved, strict=True))
    ):
        raise ValueError("QTUM supplement/source mismatch")
    names = sorted({r["symbol"] for r in plan["files"]})
    population = inputs["population"]["symbols"]
    if len(names) != 81 or len(population) != 924 or not set(names) <= set(population):
        raise ValueError("frozen archive population mismatch")
    policy = {
        "launches": {
            "DEFIUSDT": stamp("2020-08-28T07:00:00+00:00"),
            "AAVEUSDT": stamp("2020-10-16T07:00:00+00:00"),
        },
        "settlements": {"LENDUSDT": stamp("2020-10-10T00:00:00+00:00")},
        "proposed_launches": {"QTUMUSDT": stamp("2020-02-20T08:00:00+00:00")},
        "indices": ["DEFIUSDT"],
    }
    return (
        plan["files"],
        names,
        population,
        february,
        api_rows,
        sources["qtum_funding"][1],
        policy,
        {key: digest(body) for key, body in bodies.items()},
    )


def save_table(target, table):
    """Reuse equal unmanifested output after interruption;never overwrite conflicts."""
    if target.exists():
        body = target.read_bytes()
        if not table.equals(pq.read_table(pa.BufferReader(body), use_threads=False)):
            raise ValueError("existing Parquet content conflict: " + str(target))
        return digest(body)
    target.parent.mkdir(parents=True, exist_ok=True)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="zstd")
    body = sink.getvalue().to_pybytes()
    if not table.equals(pq.read_table(pa.BufferReader(body), use_threads=False)):
        raise ValueError("Parquet round-trip inequality")
    temporary = target.with_suffix(".parquet.part")
    temporary.write_bytes(body)
    temporary.replace(target)
    return digest(body)


def build_symbol(symbol, items, output, february, api_meta, policy, api_rows):
    index_path = output / "index" / (symbol + ".json")
    cached = index_path.exists()
    previous = read_json(index_path) if cached else None
    trade, mark, funding, parts, sources = {}, {}, [], [], {}
    row_counts, quarantines = Counter(), Counter()
    source_total = 0
    if cached:
        for part in previous["partitions"]:
            if digest((output / part["relative_path"]).read_bytes()) != part["parquet_sha256"]:
                raise ValueError("output checkpoint Parquet SHA mismatch")
        if digest((output / previous["daily_path"]).read_bytes()) != previous["daily_sha256"]:
            raise ValueError("daily checkpoint SHA mismatch")

    def retain(table, kind, month):
        path = f"observations/{kind}/{symbol}/{month}.parquet"
        sha = save_table(output / path, table)
        parts.append(
            {
                "relative_path": path,
                "parquet_sha256": sha,
                "kind": kind,
                "month": month,
                "rows": table.num_rows,
            }
        )
        row_counts[kind] += table.num_rows
        quarantines[kind] += sum(table["quarantine_from_trading_reconstruction"].to_pylist())
        if kind == "funding":
            funding.extend(table.select(FUND_FIELDS).to_pylist())
        else:
            target = trade if kind == "trade" else mark
            for row in table.select(BAR_FIELDS).to_pylist():
                if row["bar_open_ms"] in target:
                    raise ValueError("duplicate hourly observation across partitions")
                target[row["bar_open_ms"]] = row

    for item in sorted(items, key=lambda row: (row["kind"], row["month"])):
        verified, _ = check_file(item, output / "source_verification")
        sources[item["key"]] = {
            key: verified[key] for key in ("sha256", "report_sha256", "metadata_sha256")
        }
        source_total += verified["quality"]["row_count"]
        if symbol == "QTUMUSDT" and item["kind"] == "funding" and item["month"] == "2020-03":
            if not overlap_check(api_rows, verified["funding_events"])["rate_matches"]:
                raise ValueError("QTUM March overlap changed")
        if not cached:
            report_body = (
                SOURCE / "download/files" / (digest(item["key"].encode()) + ".json")
            ).read_bytes()
            if digest(report_body) != verified["report_sha256"]:
                raise ValueError("source report changed during normalization")
            record = json.loads(report_body)
            filename = item["key"].rsplit("/", 1)[-1]
            table = normalize_base(
                parse_csv(resolve_raw(item, DATA).read_bytes(), filename, item["kind"]), record
            )
            if table.num_rows != verified["quality"]["row_count"]:
                raise ValueError("normalized/raw row count mismatch")
            retain(add_flags(table, symbol, item["kind"], policy), item["kind"], item["month"])
    if cached:
        if previous["sources"] != sources or previous["source_rows"] != source_total:
            raise ValueError("source checkpoint conflict")
        return previous, True
    supplement = 0
    if symbol == "QTUMUSDT":
        if any(r["kind"] == "funding" and r["month"] == "2020-02" for r in items):
            raise ValueError("API supplement would collide with archive partition")
        retain(api_table(february, api_meta, policy), "funding", "2020-02")
        supplement = len(february)
    if sum(row_counts.values()) != source_total + supplement:
        raise ValueError("output row conservation failed")
    rows = daily_rows(symbol, trade, mark, funding, policy)
    if len(rows) != 366:
        raise ValueError("daily calendar row count mismatch")
    daily_path = f"daily/{symbol}.parquet"
    daily_sha = save_table(output / daily_path, daily_table(rows))
    result = {
        "instrument_id": symbol,
        "sources": sources,
        "source_rows": source_total,
        "partitions": parts,
        "rows_by_kind": dict(row_counts),
        "supplement_rows": supplement,
        "quarantined_observations_by_kind": dict(quarantines),
        "daily_path": daily_path,
        "daily_sha256": daily_sha,
        "daily_rows": len(rows),
        "price_history_diagnostic_days": sum(r["price_history_diagnostic_candidate"] for r in rows),
        "historical_strategy_eligible": False,
    }
    write_json(index_path, result)
    return result, False


def run(args):
    if args.action == "summary":
        for folder in (PILOT, FULL):
            path = folder / "manifest.json"
            print(
                json.dumps({"path": str(path), **read_json(path)})
                if path.exists()
                else f"{path}: not run"
            )
        return
    started = time.monotonic()
    files, names, population, february, api_rows, meta, policy, hashes = load_inputs()
    selected = sorted(SYMBOLS) if args.action == "pilot" else names
    output = PILOT if args.action == "pilot" else FULL
    binding = {
        "schema": 2,
        "source_hashes": hashes,
        "symbols": selected,
        "window": ["2020-01-01", "2021-01-01"],
        "script_sha256": digest(Path(__file__).read_bytes()),
        "dependencies": {
            name: digest((ROOT / "scripts" / name).read_bytes())
            for name in (
                "early_research_rules.py",
                "build_research_data.py",
                "audit_history_extension.py",
                "audit_usdm_acquisition.py",
                "check_early_cases.py",
                "acquire_usdm_universe.py",
                "check_lifecycle_rows.py",
                "review_contract_identity.py",
                "collect_cmc_weekly.py",
            )
        },
    }
    with exclusive_run(output / ".build.lock"):
        bind_run(output, binding)
        results, hits = [], 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = [
                pool.submit(
                    build_symbol,
                    symbol,
                    [r for r in files if r["symbol"] == symbol],
                    output,
                    february,
                    meta,
                    policy,
                    api_rows,
                )
                for symbol in selected
            ]
            for number, job in enumerate(as_completed(jobs), 1):
                item, cached = job.result()
                results.append(item)
                hits += int(cached)
                if number % 10 == 0 or number == len(jobs):
                    print(f"early research {number}/{len(jobs)}; cache_hits={hits}", flush=True)
        row_counts, quarantine = Counter(), Counter()
        for result in results:
            row_counts.update(result["rows_by_kind"])
            quarantine.update(result["quarantined_observations_by_kind"])
        partitions = sum(len(r["partitions"]) for r in results)
        if args.action == "full" and (
            partitions != 1527
            or row_counts["funding"] != 43058
            or sum(r["daily_rows"] for r in results) != 29646
        ):
            raise ValueError("registered full release count mismatch")
        write_json(
            output / "universe_coverage.json",
            [
                {
                    "instrument_id": symbol,
                    "early_archive_files": sum(r["symbol"] == symbol for r in files),
                    "absent_files_do_not_prove_nonlisting": True,
                }
                for symbol in population
            ],
        )
        ledger = [
            {
                "instrument_id": symbol,
                "known_identity_reuse": False,
                "official_events": [
                    {
                        "event_type": kind,
                        "effective_at": datetime.fromtimestamp(
                            values[symbol] / 1000, tz=UTC
                        ).isoformat(),
                        "publication_vintage_proven": False,
                    }
                    for kind, values in (
                        ("launch", policy["launches"]),
                        ("automatic_settlement", policy["settlements"]),
                    )
                    if symbol in values
                ],
                "full_lifecycle_proven": False,
                "lifecycle_origin_unverified": symbol not in policy["launches"],
            }
            for symbol in selected
        ]
        write_json(output / "lifecycle/identity_ledger.json", ledger)
        write_json(output / "lifecycle/review_policy.json", policy)
        result = {
            "success": True,
            "errors": [],
            "schema": 2,
            "full_scope": args.action == "full",
            "identifiers": len(results),
            "source_partitions_verified": sum(len(r["sources"]) for r in results),
            "normalized_partitions": partitions,
            "rows_by_kind": dict(row_counts),
            "qtum_supplement_rows": sum(r["supplement_rows"] for r in results),
            "daily_rows": sum(r["daily_rows"] for r in results),
            "quarantined_observations_by_kind": dict(quarantine),
            "cache_hits": hits,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "historical_size_integrated": False,
            "qtum_launch_source_gate_resolved": False,
            "historical_eligible_universe_ready": False,
            "funding_cashflows_verified": False,
            "publication_times_proven": False,
            "partial_2019_samples_integrated": False,
            "factor_values_computed": False,
            "label_values_computed": False,
            "OOS_performance_inspected": False,
        }
        write_json(output / "manifest.json", result)
        print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pilot", "full", "summary"))
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    log = ROOT / "reports/acquisition" / f"early_research_{args.action}_20261119.log"
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
