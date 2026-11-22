"""Resumable official-source verification; additive observations, never canonical overwrite."""

import csv
import hashlib
import io
import json
import math
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from .config import DAY, HOUR, load_json, sha


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def millis(day):
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


def make_plan(root, dataset, review):
    root, dataset, review = Path(root), Path(dataset), Path(review)
    manifest = load_json(dataset / "manifest.json")
    summary = load_json(review / "summary.json")
    if not manifest["success"] or summary["dataset_manifest_sha256"] != sha(
        dataset / "manifest.json"
    ):
        raise ValueError("Dataset/review identity mismatch")
    for name, expected in summary["output_hashes"].items():
        if sha(review / name) != expected:
            raise ValueError("Reviewed source changed: " + name)
    for name, expected in manifest["output_hashes"].items():
        if sha(dataset / name) != expected:
            raise ValueError("Dataset source changed: " + name)
    queue = pd.read_csv(review / "reviewed_queue.csv")
    queue = queue.astype(object).where(pd.notna(queue), "")
    jobs, cases = {}, []
    daily_root = root / manifest["build_identity"]["settings"]["daily_root"]
    hourly_root = root / manifest["build_identity"]["settings"]["hourly_root"]
    for item in queue.to_dict("records"):
        case = dict(item)
        case["case_id"] = digest(
            {k: item[k] for k in ["instrument_id", "issue", "from_data_day", "through_data_day"]}
        )[:20]
        case["job_ids"] = []
        symbol = item["instrument_id"]
        disposition = item["review_disposition"]
        if disposition in {"initial_listing_flow_warmup", "known_effective_stop"}:
            case["initial_disposition"] = disposition
        elif item["issue"] == "regular_execution_review":
            case["initial_disposition"] = "phase_evidence_unresolved"
        else:
            case["initial_disposition"] = "source_verification_pending"
            if item["issue"] == "funding_input_review":
                start = millis(item["from_data_day"]) + DAY - 7 * DAY - HOUR
                stop = millis(item["through_data_day"]) + 2 * DAY
                windows = [(x, min(x + 28 * DAY, stop)) for x in range(start, stop, 28 * DAY)]
                definitions = [("funding", a, b) for a, b in windows]
            else:
                kind = "mark" if item["issue"] == "missing_snapshot_mark" else "trade"
                if item["issue"] == "flow_input_repair":
                    days = json.loads(item["underlying_source_days"])
                else:
                    days = (
                        pd.date_range(item["from_data_day"], item["through_data_day"])
                        .strftime("%Y-%m-%d")
                        .tolist()
                    )
                if kind == "mark" and len(days) > 1:
                    a, b = millis(days[0]), millis(days[-1]) + DAY
                    definitions = [(kind, x, min(x + 28 * DAY, b)) for x in range(a, b, 28 * DAY)]
                else:
                    definitions = [(kind, millis(day), millis(day) + DAY) for day in days]
            for kind, start, stop in definitions:
                definition = {"symbol": symbol, "kind": kind, "start_ms": start, "stop_ms": stop}
                job_id = digest(definition)[:20]
                case["job_ids"].append(job_id)
                if job_id not in jobs:
                    months = pd.period_range(
                        pd.Timestamp(start - 8 * HOUR, unit="ms"),
                        pd.Timestamp(stop + 8 * HOUR, unit="ms"),
                        freq="M",
                    ).astype(str)
                    baselines = {}
                    for month in months:
                        path = hourly_root / "observations" / kind / symbol / (month + ".parquet")
                        expected = manifest["source_bindings"].get(str(path))
                        if path.exists():
                            # Trade/mark monthly sources are bound by their canonical indices.
                            if expected is None:
                                key = f"data/futures/um/monthly/{'klines' if kind == 'trade' else 'markPriceKlines'}/{symbol}/1h/{symbol}-1h-{month}.zip"
                                index = (
                                    hourly_root
                                    / "index"
                                    / (hashlib.sha256(key.encode()).hexdigest() + ".json")
                                )
                                meta = load_json(index)
                                daily_index = load_json(daily_root / "index" / (symbol + ".json"))
                                binding = daily_index["sources"][key]
                                if (
                                    sha(index) != binding["index_sha256"]
                                    or meta["parquet_sha256"] != binding["parquet_sha256"]
                                ):
                                    raise ValueError("Hourly index binding mismatch: " + key)
                                expected = binding["parquet_sha256"]
                            if sha(path) != expected:
                                raise ValueError("Hourly input changed: " + str(path))
                            baselines[str(path)] = expected
                    jobs[job_id] = definition | {"job_id": job_id, "baselines": baselines}
        cases.append(case)
    plan = {
        "dataset": str(dataset.resolve()),
        "dataset_manifest_sha256": sha(dataset / "manifest.json"),
        "review_summary_sha256": sha(review / "summary.json"),
        "code_sha256": sha(Path(__file__)),
        "registration_sha256": sha(root / "experiments/018_full_catalog_source_repair.md"),
        "jobs": jobs,
        "cases": cases,
    }
    plan_id = digest(plan)[:20]
    output = root / "data/repairs/full_universe" / plan_id
    path = output / "plan.json"
    if path.exists() and load_json(path) != plan:
        raise ValueError("Repair plan collision")
    write_json(path, plan)
    print(
        json.dumps(
            {
                "repair_dir": str(output),
                "cases": len(cases),
                "jobs": len(jobs),
                "jobs_by_kind": pd.Series([j["kind"] for j in jobs.values()])
                .value_counts()
                .to_dict(),
            }
        ),
        flush=True,
    )
    return output


class RateGate:
    def __init__(self, seconds=0.7):
        self.seconds = seconds
        self.lock = threading.Lock()
        self.last = 0.0
        self.halted = threading.Event()

    def wait(self):
        with self.lock:
            if self.halted.is_set():
                raise RuntimeError("Requests halted after exchange rate limit")
            time.sleep(max(0, self.seconds - (time.monotonic() - self.last)))
            self.last = time.monotonic()


def request(url, folder, gate):
    """Persist every response, including HTTP error bodies; retry transient failures only."""
    folder.mkdir(parents=True, exist_ok=True)
    for _attempt in range(3):
        gate.wait()
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        raw_path = folder / (stamp + ".raw")
        status, body, error = None, b"", None
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "crypto-factor-research/0.2"}),
                timeout=20,
            ) as response:
                status = response.status
                body = response.read(8 * 1024 * 1024 + 1)
            if len(body) > 8 * 1024 * 1024:
                raise ValueError("Response size bound exceeded")
        except urllib.error.HTTPError as exc:
            status, body, error = exc.code, exc.read(16384), str(exc)
        except Exception as exc:
            error = str(exc)
        raw_path.write_bytes(body)
        record = {
            "url": url,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "status": status,
            "error": error,
            "path": str(raw_path.resolve()),
            "sha256": sha(raw_path),
            "bytes": len(body),
        }
        write_json(raw_path.with_suffix(".json"), record)
        if status in {418, 429}:
            gate.halted.set()
        if status == 200:
            return body, record
        if status is not None and status < 500:
            break
    raise ValueError(json.dumps(record))


def parse_klines(rows, job):
    if not isinstance(rows, list):
        raise ValueError("Kline response is not an array")
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, list) or len(row) < 12:
            raise ValueError("Malformed kline")
        t = int(row[0])
        values = [float(row[i]) for i in [1, 2, 3, 4, 5, 7, 9, 10]]
        o, h, low, c, vol, quote, buy, buy_quote = values
        if (
            t in seen
            or t % HOUR
            or not job["start_ms"] <= t < job["stop_ms"]
            or int(row[6]) != t + HOUR - 1
        ):
            raise ValueError("Duplicate/out-of-window/invalid kline timestamp")
        if (
            not all(math.isfinite(v) for v in values)
            or min(o, h, low, c) <= 0
            or h < max(o, c, low)
            or low > min(o, c)
            or min(vol, quote, buy, buy_quote) < 0
            or buy > vol + 1e-8
            or buy_quote > quote + 1e-8
        ):
            raise ValueError("Invalid kline price/volume bounds")
        seen.add(t)
        result.append({"timestamp_ms": t, "values": row})
    if [x["timestamp_ms"] for x in result] != sorted(seen):
        raise ValueError("Unordered klines")
    return result


def parse_funding(rows, job):
    if not isinstance(rows, list) or len(rows) >= 1000:
        raise ValueError("Funding response malformed or pagination bound reached")
    result, seen = [], set()
    for row in rows:
        t, value = int(row["fundingTime"]), float(row["fundingRate"])
        if (
            row["symbol"] != job["symbol"]
            or t in seen
            or not job["start_ms"] <= t < job["stop_ms"]
            or not math.isfinite(value)
        ):
            raise ValueError("Funding identity/timestamp/value mismatch")
        seen.add(t)
        result.append(
            {"timestamp_ms": t, "rate": value, "rate_type": row.get("rateType", "unspecified")}
        )
    if [r["timestamp_ms"] for r in result] != sorted(seen):
        raise ValueError("Unordered funding")
    return result


def baseline(job):
    frames = []
    for path, expected in job["baselines"].items():
        if sha(path) != expected:
            raise ValueError("Bound baseline changed: " + path)
        columns = (
            ["event_timestamp_ms", "funding_rate", "funding_interval_hours"]
            if job["kind"] == "funding"
            else [
                "bar_open_ms",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_volume",
                "taker_buy_volume",
                "taker_buy_quote_volume",
            ]
        )
        frames.append(pq.read_table(path, columns=columns).to_pandas())
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def compare_observations(job, rows, source):
    prior = baseline(job)
    column = "event_timestamp_ms" if job["kind"] == "funding" else "bar_open_ms"
    known = {int(row[column]): row for row in prior.to_dict("records")} if len(prior) else {}
    additions, conflicts = [], []
    for row in rows:
        t = row["timestamp_ms"]
        if t in known:
            old = known[t]
            if job["kind"] == "funding":
                matches = math.isclose(
                    float(old["funding_rate"]), row["rate"], rel_tol=1e-10, abs_tol=1e-12
                )
            else:
                matches = all(
                    math.isclose(
                        float(old[name]), float(row["values"][i]), rel_tol=1e-10, abs_tol=1e-12
                    )
                    for i, name in [
                        (1, "open"),
                        (2, "high"),
                        (3, "low"),
                        (4, "close"),
                        (5, "volume"),
                        (7, "quote_volume"),
                        (9, "taker_buy_volume"),
                        (10, "taker_buy_quote_volume"),
                    ]
                )
            if not matches:
                conflicts.append(t)
        else:
            entry = {
                "kind": job["kind"],
                "symbol": job["symbol"],
                **row,
                "source": row.get("source_override", source),
            }
            if job["kind"] == "funding":
                before = prior[prior.event_timestamp_ms.lt(t)] if len(prior) else prior
                after = prior[prior.event_timestamp_ms.gt(t)] if len(prior) else prior
                interval = None
                if len(before) and len(after):
                    a, b = before.iloc[-1], after.iloc[0]
                    duration = float(a.funding_interval_hours)
                    if (
                        duration == float(b.funding_interval_hours)
                        and duration > 0
                        and abs((t - int(a.event_timestamp_ms)) % int(duration * HOUR)) <= 1000
                    ):
                        interval = duration
                entry["funding_interval_hours"] = interval
                entry["interval_evidence"] = (
                    "equal_adjacent_recorded_intervals" if interval else "unverified"
                )
            additions.append(entry)
    return additions, conflicts


def old_daily_caches(root):
    roots = [
        root / "data/interim/development_mark_recovery",
        root / "data/interim/usdm_universe/mark_recovery_daily_20261117",
    ]
    result = {}
    for directory in roots:
        for path in directory.rglob("result.json"):
            try:
                item = load_json(path)
                if item.get("success") and "date" in item and "zip_path" in item:
                    result[(item["symbol"], item["date"])] = path
            except (OSError, ValueError, KeyError):
                continue
    return result


def cached_daily(path, job):
    meta = load_json(path)

    def member(name):
        p = (path.parent / meta[name]).resolve()
        if not p.is_relative_to(path.parent.resolve()):
            raise ValueError("Old cache path escape")
        return p

    raw, check = member("zip_path"), member("checksum_path")
    if sha(raw) != meta["source_sha256"] or sha(raw) != check.read_text().split()[0]:
        raise ValueError("Old daily cache checksum mismatch")
    if not meta["source_url"].startswith("https://data.binance.vision/"):
        raise ValueError("Nonofficial cache source")
    return unzip_daily(raw.read_bytes(), job), {
        "url": meta["source_url"],
        "path": str(raw),
        "sha256": sha(raw),
        "retrieved_at": meta.get("source_retrieved_at"),
        "local_cache_reused": True,
        "checksum_path": str(check),
        "checksum_sha256": sha(check),
    }


def unzip_daily(body, job, archive_month=None):
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        entries = archive.infolist()
        if len(entries) != 1 or entries[0].file_size > 8 * 1024 * 1024:
            raise ValueError("Unexpected daily archive content")
        expected = f"{job['symbol']}-1h-{archive_month or pd.Timestamp(job['start_ms'], unit='ms').strftime('%Y-%m-%d')}.csv"
        if entries[0].filename != expected:
            raise ValueError("Daily archive filename mismatch")
        rows = list(csv.reader(io.StringIO(archive.read(entries[0]).decode("utf-8-sig"))))
    return parse_klines(
        [
            row
            for row in rows
            if row and row[0] != "open_time" and job["start_ms"] <= int(row[0]) < job["stop_ms"]
        ],
        job,
    )


def verify_job(job, output, gate, local, retry_failed=False):
    folder = output / "jobs" / job["job_id"]
    path = folder / "result.json"
    fingerprint = digest(job)
    if path.exists():
        if sha(path) != path.with_suffix(".sha256").read_text().strip():
            raise ValueError("Cached result metadata changed")
        previous = load_json(path)
        if previous.get("job_fingerprint") != fingerprint:
            raise ValueError("Cached job identity mismatch")
        for source in previous.get("sources", []):
            if sha(source["path"]) != source["sha256"]:
                raise ValueError("Cached response body changed")
            if (
                "checksum_path" in source
                and sha(source["checksum_path"]) != source["checksum_sha256"]
            ):
                raise ValueError("Cached checksum changed")
        baseline(job)
        if not (retry_failed and previous.get("status") == "unresolved_source_request"):
            return previous | {"cache_hit": True}
    result = {
        "job_id": job["job_id"],
        "job_fingerprint": fingerprint,
        "kind": job["kind"],
        "symbol": job["symbol"],
        "sources": [],
        "additions": [],
        "conflicts": [],
        "cache_hit": False,
    }
    try:
        day = pd.Timestamp(job["start_ms"], unit="ms").strftime("%Y-%m-%d")
        cache = (
            local.get((job["symbol"], day))
            if job["kind"] == "mark" and job["stop_ms"] - job["start_ms"] == DAY
            else None
        )
        if cache:
            rows, source = cached_daily(cache, job)
            result["sources"].append(source)
        else:
            endpoint = {"funding": "fundingRate", "mark": "markPriceKlines", "trade": "klines"}[
                job["kind"]
            ]
            params = {
                "symbol": job["symbol"],
                "startTime": job["start_ms"],
                "endTime": job["stop_ms"] - 1,
                "limit": 1000,
            }
            if job["kind"] != "funding":
                params["interval"] = "1h"
            url = (
                "https://fapi.binance.com/fapi/v1/"
                + endpoint
                + "?"
                + urllib.parse.urlencode(params)
            )
            rows = None
            try:
                body, source = request(url, folder / "responses", gate)
                result["sources"].append(source)
                rows = (
                    parse_funding(json.loads(body), job)
                    if job["kind"] == "funding"
                    else parse_klines(json.loads(body), job)
                )
            except Exception as exc:
                result["rest_error"] = str(exc)
            if rows is None and job["kind"] == "funding":
                raise ValueError(result["rest_error"])
            if (rows is None or not rows) and job["kind"] != "funding":
                product = "markPriceKlines" if job["kind"] == "mark" else "klines"
                monthly = job["stop_ms"] - job["start_ms"] > DAY
                periods = (
                    pd.period_range(
                        pd.Timestamp(job["start_ms"], unit="ms"),
                        pd.Timestamp(job["stop_ms"] - 1, unit="ms"),
                        freq="M",
                    )
                    .astype(str)
                    .tolist()
                    if monthly
                    else [day]
                )
                rows = []
                for period in periods:
                    filename = f"{job['symbol']}-1h-{period}.zip"
                    relative = f"data/futures/um/{'monthly' if monthly else 'daily'}/{product}/{job['symbol']}/1h/{filename}"
                    url = "https://data.binance.vision/" + urllib.parse.quote(relative, safe="/")
                    check, proof = request(url + ".CHECKSUM", folder / "responses", gate)
                    body, source = request(url, folder / "responses", gate)
                    if hashlib.sha256(body).hexdigest() != check.decode().split()[0]:
                        raise ValueError("Downloaded archive checksum mismatch")
                    source.update(checksum_path=proof["path"], checksum_sha256=proof["sha256"])
                    result["sources"].append(source)
                    # Each month's additions retain that month's exact source, not the last response.
                    part = unzip_daily(body, job, period if monthly else None)
                    for entry in part:
                        entry["source_override"] = source
                    rows.extend(part)
        additions, conflicts = compare_observations(job, rows, source)
        result.update(
            additions=additions,
            conflicts=conflicts,
            returned_rows=len(rows),
            returned_timestamps=[row["timestamp_ms"] for row in rows],
        )
        result["status"] = (
            "source_conflict"
            if conflicts
            else "new_observations_verified"
            if additions
            else "official_response_no_new_observations"
        )
    except Exception as exc:
        result.update(status="unresolved_source_request", error=str(exc))
    write_json(path, result)
    path.with_suffix(".sha256").write_text(sha(path) + "\n")
    return result


def _run_repairs(root, output, workers=4, retry_failed=False):
    root, output = Path(root), Path(output)
    plan = load_json(output / "plan.json")
    if plan["code_sha256"] != sha(Path(__file__)):
        raise ValueError("Repair implementation differs from bound plan; create a new plan")
    if sha(Path(plan["dataset"]) / "manifest.json") != plan["dataset_manifest_sha256"]:
        raise ValueError("Repair dataset changed")
    local, gate, results = old_daily_caches(root), RateGate(), {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(verify_job, job, output, gate, local, retry_failed): key
            for key, job in plan["jobs"].items()
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                results[key] = {
                    "job_id": key,
                    "status": "integrity_failure",
                    "error": str(exc),
                    "additions": [],
                    "conflicts": [],
                }
            if len(results) % 50 == 0:
                print(
                    json.dumps(
                        {
                            "jobs_completed": len(results),
                            "total": len(futures),
                            "statuses": pd.Series([x["status"] for x in results.values()])
                            .value_counts()
                            .to_dict(),
                        }
                    ),
                    flush=True,
                )
    cases = []
    for item in plan["cases"]:
        case = dict(item)
        responses = [results[key] for key in item["job_ids"]]
        if not responses:
            status = item["initial_disposition"]
        elif any(r["status"] in {"source_conflict", "integrity_failure"} for r in responses):
            status = "blocked_source_conflict_or_integrity"
        elif any(r["status"] == "unresolved_source_request" for r in responses):
            status = "unresolved_source_request"
        elif any(r.get("additions") for r in responses):
            status = "verified_additions_pending_integration"
        else:
            status = "official_check_no_additions_unresolved"
        case["final_disposition"] = status
        case["verified_new_rows"] = sum(len(r.get("additions", [])) for r in responses)
        case["job_ids"] = json.dumps(item["job_ids"])
        cases.append(case)
    pd.DataFrame(cases).to_csv(output / "case_dispositions.csv", index=False)
    overlay = []
    for key in sorted(results):
        value = results[key]
        if value["status"] == "new_observations_verified":
            overlay.extend(value["additions"])
    with (output / "verified_observations.jsonl").open("w") as stream:
        for row in overlay:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    request_records = [load_json(p) for p in output.glob("jobs/*/responses/*.json")]
    summary = {
        "request_count_total": len(request_records),
        "http_status_counts": pd.Series([str(r["status"]) for r in request_records])
        .value_counts()
        .to_dict(),
        "verification_pass_completed": True,
        "all_data_issues_resolved": False,
        "cases_accounted": len(cases),
        "jobs_accounted": len(results),
        "job_status_counts": pd.Series([r["status"] for r in results.values()])
        .value_counts()
        .to_dict(),
        "case_disposition_counts": pd.Series([r["final_disposition"] for r in cases])
        .value_counts()
        .to_dict(),
        "new_rows_by_kind": pd.Series([r["kind"] for r in overlay]).value_counts().to_dict(),
        "cache_hits": sum(bool(r.get("cache_hit")) for r in results.values()),
        "execution_ready": False,
        "PnL_computed": False,
        "plan_sha256": sha(output / "plan.json"),
        "output_hashes": {
            name: sha(output / name)
            for name in ["case_dispositions.csv", "verified_observations.jsonl"]
        },
    }
    write_json(output / "summary.json", summary)
    print(json.dumps(summary), flush=True)
    return summary


def run_repairs(root, output, workers=4, retry_failed=False):
    import fcntl

    output = Path(output)
    with (output / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another source-repair pass is active") from None
        return _run_repairs(root, output, workers, retry_failed)
