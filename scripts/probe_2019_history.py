"""Three fixed public BTC API samples; availability evidence only, not a backfill."""

from __future__ import annotations

import json
import math
import sys
import traceback
import urllib.parse
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from check_research_inputs import fetch
from collect_cmc_weekly import LogTee

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/interim/usdm_universe/history_extension_20261118/api_2019_probe"
START = int(datetime(2019, 9, 14, tzinfo=UTC).timestamp() * 1000)
END = START + 3600000 - 1
ENDPOINTS = {"trade": "klines", "mark": "markPriceKlines", "funding": "fundingRate"}


def assess(payload, kind, start, end):
    if not isinstance(payload, list):
        raise ValueError("expected public API list")
    if len(payload) > 2:
        raise ValueError("response exceeds requested limit")
    times, prices = [], []
    for row in payload:
        if kind == "funding":
            stamp = row["fundingTime"]
            if row["symbol"] != "BTCUSDT" or not math.isfinite(float(row["fundingRate"])):
                raise ValueError("invalid funding identity/rate")
            price = row.get("markPrice")
            prices.append(bool(price and math.isfinite(float(price)) and float(price) > 0))
        else:
            if len(row) < 7 or any(not math.isfinite(float(p)) or float(p) <= 0 for p in row[1:5]):
                raise ValueError("invalid bar")
            stamp = row[0]
        if type(stamp) is not int or not start <= stamp <= end or stamp in times:
            raise ValueError("API ignored historical bounds or duplicated events")
        times.append(stamp)
    if times != sorted(times):
        raise ValueError("API timestamps not ordered")
    return {
        "observed_rows": len(payload),
        "first_timestamp_ms": min(times, default=None),
        "last_timestamp_ms": max(times, default=None),
        "sample_available": bool(times),
        "all_sample_funding_mark_prices_present": bool(prices) and all(prices),
        "full_2019_coverage_proven": False,
    }


def run():
    binding = {
        "symbol": "BTCUSDT",
        "start_ms": START,
        "bar_end_ms": END,
        "funding_end_ms": START + 86400000 - 1,
        "maximum_requests": 3,
        "script_sha256": digest(Path(__file__).read_bytes()),
        "dependencies": {
            name: digest((ROOT / "scripts" / name).read_bytes())
            for name in ("check_research_inputs.py", "acquire_usdm_universe.py")
        },
    }
    with exclusive_run(OUTPUT / ".probe.lock"):
        bind_run(OUTPUT, binding)
        results, stopped = [], False
        for kind, endpoint in ENDPOINTS.items():
            end = START + 86400000 - 1 if kind == "funding" else END
            params = {"symbol": "BTCUSDT", "startTime": START, "endTime": end, "limit": 2}
            if kind != "funding":
                params["interval"] = "1h"
            url = (
                "https://fapi.binance.com/fapi/v1/"
                + endpoint
                + "?"
                + urllib.parse.urlencode(params)
            )
            target = OUTPUT / (kind + ".json")
            if target.exists():
                result = read_json(target)
                if result["url"] != url:
                    raise ValueError("probe endpoint binding changed")
                if result.get("source"):
                    body, report = fetch(url, OUTPUT / "requests", maximum=1024 * 1024)
                    if report["sha256"] != result["source"]["sha256"]:
                        raise ValueError("probe cache changed")
            elif stopped:
                result = {
                    "kind": kind,
                    "url": url,
                    "sample_available": False,
                    "status": "not_requested_after_access_stop",
                }
                write_json(target, result)
            else:
                print("2019 bounded probe: " + kind, flush=True)
                try:
                    body, report = fetch(url, OUTPUT / "requests", maximum=1024 * 1024)
                    result = {"kind": kind, "url": url, "source": report, "sample_available": False}
                    if report["http_status"] == 200:
                        result.update(
                            assess(json.loads(body), kind, START, end), status="sample_checked"
                        )
                    else:
                        result["status"] = "http_failure"
                except (OSError, TimeoutError) as exc:
                    result = {
                        "kind": kind,
                        "url": url,
                        "status": "transport_failure",
                        "error": str(exc),
                        "sample_available": False,
                    }
                write_json(target, result)
            stopped |= result.get("source", {}).get("http_status") in (401, 402, 403, 429, 451)
            results.append(result)
        summary = {
            "success": all(r.get("status") == "sample_checked" for r in results),
            "results": results,
            "full_2019_coverage_proven": False,
            "historical_eligible_universe_ready": False,
            "OOS_performance_inspected": False,
        }
        write_json(OUTPUT / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))


def main():
    log = ROOT / "reports/acquisition/history_extension_api_2019_20261118.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    print("Log: " + str(log), flush=True)
    with (
        log.open("a", encoding="utf-8") as handle,
        redirect_stdout(LogTee(sys.stdout, handle)),
        redirect_stderr(LogTee(sys.stderr, handle)),
    ):
        try:
            run()
        except Exception:
            traceback.print_exc()
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
