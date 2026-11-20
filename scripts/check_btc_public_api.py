"""Bounded public BTC metadata/2020 observation audit; never updates trading inputs."""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

import pyarrow.parquet as pq
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from collect_cmc_weekly import Downloader, LogTee, checked_source
from followup_early_identities import article_check
from run_early_identity import repo_path, verify_attempts, verify_output_hashes

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/btc_public_api_20261120.json"
HOUR = 3_600_000
TRADE_FIELDS = {
    1: "open_raw",
    2: "high_raw",
    3: "low_raw",
    4: "close_raw",
    5: "volume_raw",
    7: "quote_volume_raw",
    9: "taker_buy_volume_raw",
    10: "taker_buy_quote_volume_raw",
}


def number(value):
    if not isinstance(value, str):
        raise ValueError("decimal source string required")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("nonfinite decimal")
    return result


def metadata_check(payload, start):
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("symbols"), list)
        or any(not isinstance(r, dict) for r in payload["symbols"])
    ):
        raise ValueError("invalid exchangeInfo schema")
    rows = [r for r in payload["symbols"] if r.get("symbol") == "BTCUSDT"]
    if len(rows) != 1:
        raise ValueError("expected one BTCUSDT contract")
    row = rows[0]
    expected = {
        "pair": "BTCUSDT",
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "marginAsset": "USDT",
        "contractType": "PERPETUAL",
    }
    missing = [k for k, value in expected.items() if row.get(k) != value]
    onboard = row.get("onboardDate")
    if type(onboard) is not int or not 0 < onboard <= start:
        missing.append("onboardDate")
    return {
        "passed": not missing,
        "failed_fields": missing,
        "observed": {k: row.get(k) for k in ["symbol", *expected, "onboardDate", "status"]},
        "historical_rule_versions_proven": False,
    }


def timestamps(values, start, end):
    if any(type(t) is not int or not start <= t < end for t in values):
        raise ValueError("invalid observation timestamp/bounds")
    if values != sorted(set(values)):
        raise ValueError("duplicate/unordered observations")


def compare_bars(payload, archive, start, end, kind):
    if not isinstance(payload, list) or not payload or len(payload) >= 1000:
        raise ValueError("empty/invalid/saturated kline response")
    if any(not isinstance(r, list) or len(r) != 12 for r in payload):
        raise ValueError("invalid kline schema")
    actual = [r[0] for r in payload]
    timestamps(actual, start, end)
    expected = list(range(start, end, HOUR))
    archived_times = [r["bar_open_ms"] for r in archive]
    timestamps(archived_times, start, end)
    if actual != expected or archived_times != expected:
        raise ValueError("incomplete hourly API/archive coverage")
    fields = TRADE_FIELDS if kind == "trade" else {k: v for k, v in TRADE_FIELDS.items() if k <= 4}
    mismatches = []
    for row, old in zip(payload, archive, strict=True):
        if type(row[6]) is not int or row[6] != row[0] + HOUR - 1:
            raise ValueError("invalid closing timestamp")
        if any(number(row[k]) <= 0 for k in (1, 2, 3, 4)):
            raise ValueError("nonpositive price")
        for index, column in fields.items():
            if number(row[index]) != number(old[column]):
                mismatches.append(
                    {
                        "timestamp_ms": row[0],
                        "field": column,
                        "api": row[index],
                        "archive": old[column],
                    }
                )
        if kind == "trade" and (type(row[8]) is not int or row[8] != old["trade_count"]):
            mismatches.append(
                {
                    "timestamp_ms": row[0],
                    "field": "trade_count",
                    "api": row[8],
                    "archive": old["trade_count"],
                }
            )
    return {
        "passed": not mismatches,
        "rows_compared": len(payload),
        "mismatch_count": len(mismatches),
        "mismatches_first20": mismatches[:20],
    }


def compare_funding(payload, archive, start, end):
    if not isinstance(payload, list) or not payload or len(payload) >= 1000:
        raise ValueError("empty/invalid/saturated funding response")
    if any(not isinstance(r, dict) or r.get("symbol") != "BTCUSDT" for r in payload):
        raise ValueError("funding instrument mismatch")
    actual = [r["fundingTime"] for r in payload]
    timestamps(actual, start, end)
    old_times = [r["event_timestamp_ms"] for r in archive]
    timestamps(old_times, start, end)
    old_rates = {r["event_timestamp_ms"]: number(r["funding_rate_raw"]) for r in archive}
    mismatches = []
    for row in payload:
        rate = number(row["fundingRate"])
        if row.get("markPrice") not in (None, "") and number(row["markPrice"]) <= 0:
            raise ValueError("nonpositive funding mark")
        if old_rates.get(row["fundingTime"]) != rate:
            mismatches.append(
                {
                    "timestamp_ms": row["fundingTime"],
                    "api": row["fundingRate"],
                    "archive": str(old_rates.get(row["fundingTime"])),
                }
            )
    return {
        "passed": actual == old_times and not mismatches,
        "api_rows": len(payload),
        "archive_rows": len(archive),
        "timestamps_match_exactly": actual == old_times,
        "mismatch_count": len(mismatches),
        "mismatches_first20": mismatches[:20],
        "api_missing_mark_prices": sum(r.get("markPrice") in (None, "") for r in payload),
        "api_missing_reported_intervals": sum(
            r.get("fundingIntervalHours") is None for r in payload
        ),
        "funding_payments_proven": False,
    }


def capture(plan, output, fetch):
    found, outcomes = {}, {}
    downloader = Downloader(output, plan["max_raw_bytes"])
    stopped = (output / "access_pause.json").exists()
    for spec in plan["sources"]:
        label, url = spec["id"], spec["url"]
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.netloc != "fapi.binance.com"
            or parts.path
            not in {
                "/fapi/v1/exchangeInfo",
                "/fapi/v1/klines",
                "/fapi/v1/markPriceKlines",
                "/fapi/v1/fundingRate",
            }
        ):
            raise ValueError("unregistered API endpoint")
        item = checked_source(output, label, url)
        terminal = output / "terminal" / (label + ".json")
        if item is not None:
            found[label] = item[0]
            outcomes[label] = {"state": "available", "metadata": item[1]}
        elif terminal.exists():
            checkpoint = read_json(terminal)
            if checkpoint["url"] != url or checkpoint["attempt_hashes"] != verify_attempts(output):
                raise ValueError("terminal API failure evidence changed")
            outcomes[label] = {"state": "terminal_failure", "error": checkpoint["error"]}
            stopped = True
        elif stopped or not fetch:
            outcomes[label] = {"state": "not_requested", "reason": "fetch_disabled_or_stopped"}
        else:
            try:
                body, meta, _ = downloader.get(label, url)
                found[label] = body
                outcomes[label] = {"state": "available", "metadata": meta}
            except Exception as exc:
                message = str(exc)
                write_json(
                    terminal,
                    {"url": url, "error": message, "attempt_hashes": verify_attempts(output)},
                )
                outcomes[label] = {"state": "terminal_failure", "error": message}
                stopped = True
        print(f"public API {label}: {outcomes[label]['state']}", flush=True)
    return found, outcomes, downloader.requests


def load_archives(plan):
    root = ROOT.parents[1] / "data/canonical" / plan["archive_release"]
    index_body = (root / "index/BTCUSDT.json").read_bytes()
    if digest(index_body) != plan["archive_index_sha256"]:
        raise ValueError("BTC archive index changed")
    index = json.loads(index_body)
    result = {}
    for part in plan["partitions"]:
        if part not in index["partitions"]:
            raise ValueError("unregistered archive partition")
        path = (root / part["relative_path"]).resolve()
        path.relative_to(root.resolve())
        body = path.read_bytes()
        if digest(body) != part["parquet_sha256"]:
            raise ValueError("archive Parquet checksum differs")
        rows = pq.ParquetFile(io.BytesIO(body)).read().to_pylist()
        if len(rows) != part["rows"] or any(
            r["instrument_id"] != "BTCUSDT" or r["kind"] != part["kind"] or r["market"] != "usdm"
            for r in rows
        ):
            raise ValueError("archive identity/count differs")
        result[(part["kind"], part["month"])] = rows
    return result


def safe_check(function, *args):
    try:
        return function(*args)
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return {"passed": False, "error": str(exc)}


def api_check(function, body, *args):
    return safe_check(lambda: function(json.loads(body), *args))


def run(args):
    started = time.monotonic()
    plan = read_json(CONFIG)
    output = ROOT / "data/interim/btc_public_api" / args.version
    with exclusive_run(output / ".audit.lock"):
        for path, expected in plan["prior_inputs"].items():
            if digest(repo_path(path).read_bytes()) != expected:
                raise ValueError("prior BTC evidence changed: " + path)
        old_root = ROOT / "data/interim/early_identity_all/v20261119_007/full"
        verify_output_hashes(old_root, read_json(old_root / "summary.json"))
        contract = {
            "plan_sha256": digest(CONFIG.read_bytes()),
            "script_sha256": digest(Path(__file__).read_bytes()),
            "dependencies": {
                name: digest((ROOT / "scripts" / name).read_bytes())
                for name in [
                    "acquire_usdm_universe.py",
                    "collect_cmc_weekly.py",
                    "check_early_cases.py",
                    "run_early_identity.py",
                    "review_contract_identity.py",
                    "followup_early_identities.py",
                    "verify_early_size_identities.py",
                    "review_usdm_lifecycle.py",
                ]
            },
        }
        seed = output / "capture_seed.json"
        contract["capture_seed_sha256"] = digest(seed.read_bytes()) if seed.exists() else None
        if seed.exists():
            for label, expected in read_json(seed)["source_metadata_hashes"].items():
                if digest((output / "capture/raw" / (label + ".json")).read_bytes()) != expected:
                    raise ValueError("seed capture metadata changed")
        bind_run(output / "contract", contract)
        archives = load_archives(plan)
        found, outcomes, requests = capture(plan, output / "capture", args.fetch)
        checks = {}
        checks["exchange_info"] = (
            api_check(metadata_check, found["exchange_info"], plan["windows"][0]["start_ms"])
            if "exchange_info" in found
            else {"passed": False, "error": "source not captured"}
        )
        windows = {w["id"]: w for w in plan["windows"]}
        for spec in plan["sources"][1:]:
            label, kind = spec["id"], spec["kind"]
            window = windows[spec["window"]]
            start, end = window["start_ms"], window["end_ms"]
            clock = "event_timestamp_ms" if kind == "funding" else "bar_open_ms"
            selected = [r for r in archives[(kind, window["start"][:7])] if start <= r[clock] < end]
            if label not in found:
                checks[label] = {"passed": False, "error": "source not captured"}
            elif kind == "funding":
                checks[label] = api_check(compare_funding, found[label], selected, start, end)
            else:
                checks[label] = api_check(compare_bars, found[label], selected, start, end, kind)
        notice = ROOT / "data/interim/early_identity_batch1_20261119/raw/future_eth.raw"
        _, article, _ = article_check(
            notice.read_bytes(),
            "360036964392",
            [
                "second perpetual contract",
                "how to switch from btc/usdt contract to eth/usdt contract",
                "2019/11/29",
            ],
        )
        old = next(
            r for r in read_json(old_root / "asset_review.json") if r["instrument_id"] == "BTCUSDT"
        )
        prior = old["mapping_record"]["mapping"]["proof_checks"]
        sample_passed = all(c["passed"] for c in checks.values())
        assessment = {
            "instrument_id": "BTCUSDT",
            "combined_identity_evidence_satisfied": sample_passed
            and article["clauses_verified"]
            and all(
                prior[k]
                for k in [
                    "historical_identity",
                    "provider_identity",
                    "venue_name",
                    "token_contract",
                ]
            ),
            "scope_from": old["mapping_record"]["mapping"]["scope_from"],
            "scope_to_exclusive": old["mapping_record"]["mapping"]["scope_to_exclusive"],
            "prior_identity_checks": prior,
            "dated_2019_notice": article,
            "identity_registry_updated": False,
            "historical_strategy_eligible": False,
            "full_lifecycle_proven": False,
            "information_availability_proven": False,
            "funding_payments_proven": False,
            "interpretation": "Combined retrospective identity evidence and cross-channel sample consistency; not independent ground truth or full-period proof.",
        }
        write_json(output / "source_outcomes.json", outcomes)
        write_json(output / "checks.json", checks)
        write_json(output / "btc_identity_assessment.json", assessment)
        binding = {
            **contract,
            "input_hashes": plan["prior_inputs"],
            "sources": outcomes,
            "failed_attempts": verify_attempts(output / "capture"),
        }
        bind_run(output / "review", binding)
        summary = {
            "success": True,
            "public_api_capture_complete": len(found) == 7,
            "sampled_cross_check_passed": sample_passed,
            "combined_identity_evidence_satisfied": assessment[
                "combined_identity_evidence_satisfied"
            ],
            "source_http_requests_this_run": requests,
            "source_states": dict(Counter(o["state"] for o in outcomes.values())),
            "checks_passed": sum(c["passed"] for c in checks.values()),
            "checks_total": len(checks),
            "bar_rows_compared": sum(c.get("rows_compared", 0) for c in checks.values()),
            "funding_rows_compared": sum(c.get("api_rows", 0) for c in checks.values()),
            "identity_registry_updated": False,
            "canonical_joins_materialized": 0,
            "OOS_performance_inspected": False,
            "funding_cashflows_verified": False,
            "historical_eligible_universe_ready": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "output_hashes": {
                name: digest((output / name).read_bytes())
                for name in ["source_outcomes.json", "checks.json", "btc_identity_assessment.json"]
            },
        }
        write_json(output / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "summary"])
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--version", default="v20261120_002")
    args = parser.parse_args()
    if not args.version or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for c in args.version
    ):
        raise ValueError("unsafe version")
    if args.action == "summary":
        root = ROOT / "data/interim/btc_public_api" / args.version
        summary = read_json(root / "summary.json")
        verify_output_hashes(root, summary)
        print(json.dumps(summary, sort_keys=True))
        return
    path = ROOT / "reports/acquisition" / ("btc_public_api_" + args.version + ".log")
    print("Log: " + str(path), flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        path.open("a", encoding="utf-8") as log,
        redirect_stdout(LogTee(sys.stdout, log)),
        redirect_stderr(LogTee(sys.stderr, log)),
    ):
        run(args)


if __name__ == "__main__":
    main()
