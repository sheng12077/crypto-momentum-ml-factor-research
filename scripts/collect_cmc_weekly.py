"""Collect public weekly cap/identity snapshots; never compute strategy outcomes."""

from __future__ import annotations

import argparse
import http.client
import json
import sys
import time
import traceback
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from check_research_inputs import parse_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "data/interim/cmc_weekly_20261118"
LEDGER = ROOT / "data/interim/usdm_universe/lifecycle_review_20261118"
SEED = ROOT / "data/interim/research_input_readiness/20261118/responses"
PILOT = ("20201227", "20210103", "20240107", "20261025")
PER_RESPONSE = 2 * 1024**2


def requested_dates():
    start, end = date(2021, 1, 1), date(2026, 10, 31)
    cursor = start + timedelta(days=(6 - start.weekday()) % 7)
    result = [(cursor - timedelta(days=7)).strftime("%Y%m%d")]
    while cursor <= end:
        result.append(cursor.strftime("%Y%m%d"))
        cursor += timedelta(days=7)
    return result


class CalendarLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        url = urlsplit(urljoin("https://coinmarketcap.com/historical/", href))
        if url.hostname not in ("coinmarketcap.com", "www.coinmarketcap.com"):
            return
        pieces = url.path.strip("/").split("/")
        if (
            len(pieces) == 2
            and pieces[0] == "historical"
            and len(pieces[1]) == 8
            and pieces[1].isdigit()
        ):
            datetime.strptime(pieces[1], "%Y%m%d")
            self.dates.add(pieces[1])


def raw_bytes(root):
    return (
        sum(path.stat().st_size for path in (root / "raw").rglob("*.raw"))
        if (root / "raw").exists()
        else 0
    )


def checked_source(root, label, url):
    index = root / "raw" / (label + ".json")
    if not index.exists():
        return None
    report = read_json(index)
    raw = root / "raw" / (label + ".raw")
    body = raw.read_bytes()
    if (
        report["url"] != url
        or report["status"] != 200
        or report["sha256"] != digest(body)
        or report["bytes"] != len(body)
    ):
        raise ValueError("raw source cache integrity failure")
    return body, report, True


def write_source(root, label, body, report):
    target = root / "raw" / (label + ".raw")
    if target.exists() and target.read_bytes() != body:
        raise ValueError("refuse to overwrite existing raw source")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".raw.part")
    temporary.write_bytes(body)
    temporary.replace(target)
    write_json(target.with_suffix(".json"), report)


class Downloader:
    def __init__(self, root, budget, pause=2.0):
        self.root, self.budget, self.pause = root, budget, pause
        self.last = 0.0
        self.requests = 0

    def get(self, label, url):
        cached = checked_source(self.root, label, url)
        if cached is not None:
            return cached
        if label != "calendar":
            seed_index = SEED / (digest(url.encode()) + ".json")
            if seed_index.exists():
                report = read_json(seed_index)
                body = seed_index.with_suffix(".raw").read_bytes()
                if (
                    report["url"] != url
                    or digest(body) != report["sha256"]
                    or len(body) != report["bytes"]
                ):
                    raise ValueError("seed response integrity failure")
                if report["http_status"] == 200:
                    if raw_bytes(self.root) + len(body) > self.budget:
                        raise ValueError("raw byte budget exhausted")
                    report = {
                        key: report[key] for key in ("url", "sha256", "bytes", "retrieved_at")
                    }
                    report.update(status=200, reused_verified_seed=True)
                    write_source(self.root, label, body, report)
                    return body, report, True
        for attempt in range(1, 4):
            remaining = self.budget - raw_bytes(self.root)
            if remaining <= 0:
                raise ValueError("raw byte budget exhausted")
            limit = min(PER_RESPONSE, remaining)
            time.sleep(max(0, self.pause - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            self.requests += 1
            response, body, failure = None, b"", None
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "weekly-cap-research/1.0"}
                )
                try:
                    response = urllib.request.urlopen(request, timeout=30)
                except urllib.error.HTTPError as exc:
                    response = exc
                with response:
                    body = response.read(limit + 1)
                    status = response.code
                    retry_after = response.headers.get("Retry-After")
            except (OSError, TimeoutError, http.client.IncompleteRead) as exc:
                status, retry_after, failure = 0, None, str(exc)
            truncated = len(body) > limit
            saved = body[:limit]
            report = {
                "url": url,
                "status": status,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "bytes": len(saved),
                "sha256": digest(saved),
                "attempt": attempt,
                "truncated": truncated,
                "error": failure,
                "retry_after": retry_after,
            }
            if status == 200 and not truncated:
                write_source(self.root, label, saved, report)
                return saved, report, False
            audit = self.root / "raw/attempts" / label / str(time.time_ns())
            write_source(self.root, str(audit.relative_to(self.root / "raw")), saved, report)
            if status in (401, 402, 403, 429):
                until = time.time() + 300
                if retry_after:
                    try:
                        until = max(until, time.time() + float(retry_after))
                    except ValueError:
                        try:
                            until = max(until, parsedate_to_datetime(retry_after).timestamp())
                        except (ValueError, TypeError):
                            pass
                write_json(self.root / "access_pause.json", {"not_before_epoch": until, **report})
                raise ValueError(
                    f"HTTP {status}; stopped all acquisition; inspect access_pause.json before retry"
                )
            if truncated or (status and status < 500):
                raise ValueError(f"invalid/bounded source response HTTP {status}")
            if attempt < 3:
                time.sleep(2**attempt)
        raise ValueError("transport/5xx failures exhausted three attempts")


def make_plan(root, downloader):
    path = root / "plan.json"
    if path.exists():
        plan = read_json(path)
        if plan["requested_dates"] != requested_dates():
            raise ValueError("calendar plan changed")
        cached = checked_source(root, "calendar", "https://coinmarketcap.com/historical/")
        if cached is None or cached[1]["sha256"] != plan["calendar_source"]["sha256"]:
            raise ValueError("calendar source binding changed")
        return plan
    body, source, _ = downloader.get("calendar", "https://coinmarketcap.com/historical/")
    parser = CalendarLinks()
    parser.feed(body.decode("utf-8"))
    expected = requested_dates()
    plan = {
        "schema": 1,
        "requested_dates": expected,
        "expected_dates": len(expected),
        "listed_requested_dates": sorted(parser.dates & set(expected)),
        "unlisted_requested_dates": sorted(set(expected) - parser.dates),
        "carry_in_date": "20201227",
        "calendar_source": source,
        "interpretation": "first public page per weekly date; no guarantee of all-asset or PIT coverage",
    }
    write_json(path, plan)
    return plan


def partition(root, output, label, downloader):
    url = "https://coinmarketcap.com/historical/" + label + "/"
    body, source, cached = downloader.get(label, url)
    target, index = output / "partitions" / (label + ".json"), output / "index" / (label + ".json")
    if index.exists():
        previous = read_json(index)
        if (
            previous["source_sha256"] != source["sha256"]
            or digest(target.read_bytes()) != previous["parsed_sha256"]
        ):
            raise ValueError("parsed partition integrity failure")
        rows = read_json(target)
        if len(rows) != previous["rows"]:
            raise ValueError("cached row count mismatch")
        return rows, previous, True
    if target.exists():
        raise ValueError("unmanifested parsed partition; inspect rather than overwrite")
    rows = parse_snapshot(body, label)
    for row in rows:
        row["source"] = source
    write_json(target, rows)
    report = {
        "date": label,
        "rows": len(rows),
        "source_sha256": source["sha256"],
        "parsed_sha256": digest(target.read_bytes()),
    }
    write_json(index, report)
    return rows, report, cached


def mapping_review(identities, rows):
    symbols = defaultdict(lambda: defaultdict(list))
    for row in rows:
        symbols[row["symbol"].casefold()][row["vendor_asset_id"]].append(row)
    result = []
    for identity in identities:
        instrument = identity["instrument_id"]
        current = identity.get("current_product_metadata") or {}
        token = current.get("baseAsset") or instrument.removesuffix("USDT")
        candidates = []
        for vendor_id, found in sorted(symbols[token.casefold()].items()):
            candidates.append(
                {
                    "vendor_asset_id": vendor_id,
                    "names": sorted({r["name"] for r in found}),
                    "observed_dates": sorted({r["snapshot_date"] for r in found}),
                }
            )
        result.append(
            {
                "instrument_id": instrument,
                "current_base_annotation": current.get("baseAsset"),
                "current_noncoin_annotation": identity.get("current_noncoin_annotation"),
                "known_identity_reuse": identity["known_identity_reuse"],
                "candidates_for_manual_review_only": candidates,
                "candidate_ID_ambiguity": len(candidates) > 1,
                "approved_mapping": None,
                "historical_strategy_eligible": False,
            }
        )
    return result


def run(args):
    root = args.output_root
    downloader = Downloader(root, int(args.max_mib * 1024**2))
    if args.action == "summary":
        for path in (root / "plan.json", root / "pilot/summary.json", root / "full/summary.json"):
            if not path.exists():
                print(str(path) + ": not completed")
                continue
            data = read_json(path)
            if path.name == "plan.json":
                data = {
                    k: data[k]
                    for k in ("expected_dates", "carry_in_date", "unlisted_requested_dates")
                }
            print(json.dumps({"path": str(path), **data}, sort_keys=True))
        return True
    paused = root / "access_pause.json"
    if paused.exists() and time.time() < read_json(paused)["not_before_epoch"]:
        raise ValueError("source access cooldown active; inspect access_pause.json")
    if raw_bytes(root) > downloader.budget:
        raise ValueError("cached raw bytes exceed requested budget")
    plan = make_plan(root, downloader)
    if args.action == "plan":
        print(
            json.dumps(
                {
                    "planned_dates": plan["expected_dates"],
                    "unlisted_dates": plan["unlisted_requested_dates"],
                    "plan_sha256": digest((root / "plan.json").read_bytes()),
                },
                sort_keys=True,
            )
        )
        return not plan["unlisted_requested_dates"]
    selected = list(PILOT) if args.action == "pilot" else plan["requested_dates"]
    output = root / ("pilot" if args.action == "pilot" else "full")
    lifecycle = read_json(args.lifecycle_dir / "summary.json")
    ledger_bytes = (args.lifecycle_dir / "identity_ledger.json").read_bytes()
    if not lifecycle["success"] or digest(ledger_bytes) != lifecycle["ledger_sha256"]:
        raise ValueError("lifecycle ledger integrity failure")
    bind_run(
        output,
        {
            "schema": 1,
            "plan_sha256": digest((root / "plan.json").read_bytes()),
            "tool_sha256": digest(Path(__file__).read_bytes()),
            "parser_sha256": digest((ROOT / "scripts/check_research_inputs.py").read_bytes()),
            "ledger_sha256": digest(ledger_bytes),
            "selected_dates": selected,
        },
    )
    rows, reports, errors, hits = [], [], [], 0
    for number, label in enumerate(selected, 1):
        if label not in plan["listed_requested_dates"]:
            errors.append(
                {"date": label, "error": "requested date absent from frozen source calendar"}
            )
            continue
        try:
            parsed, report, cached = partition(root, output, label, downloader)
            rows.extend(parsed)
            reports.append(report)
            hits += int(cached)
        except Exception as exc:
            errors.append({"date": label, "error": str(exc)})
            break  # Fail closed on schema/access/integrity errors; never hammer remaining dates.
        if number % 10 == 0 or number == len(selected):
            print(
                f"CMC {number}/{len(selected)}; errors={len(errors)}; HTTP={downloader.requests}",
                flush=True,
            )
    review = mapping_review(json.loads(ledger_bytes), rows)
    write_json(output / "mapping_review.json", review)
    counts = Counter(r["vendor_asset_id"] for r in rows)
    write_json(output / "vendor_ID_coverage.json", {str(k): v for k, v in sorted(counts.items())})
    write_json(output / "date_coverage.json", reports)
    summary = {
        "success": not errors and len(reports) == len(selected),
        "full_scope": args.action == "download",
        "planned_dates": len(selected),
        "verified_dates": len(reports),
        "rows": len(rows),
        "distinct_vendor_IDs": len(counts),
        "dates_not_200_rows": [r["date"] for r in reports if r["rows"] != 200],
        "cache_hits": hits,
        "http_requests": downloader.requests,
        "raw_bytes": raw_bytes(root),
        "identifiers_reviewed": len(review),
        "identifiers_with_lexical_candidates": sum(
            bool(r["candidates_for_manual_review_only"]) for r in review
        ),
        "ambiguous_candidate_identifiers": sum(r["candidate_ID_ambiguity"] for r in review),
        "approved_historical_mappings": 0,
        "historical_eligible_universe_ready": False,
        "point_in_time_ready": False,
        "all_asset_coverage_proven": False,
        "OOS_performance_inspected": False,
        "errors": errors,
        "inputs": read_json(output / "run_config.json"),
    }
    write_json(output / "summary.json", summary)
    compact = {key: value for key, value in summary.items() if key != "inputs"}
    print(json.dumps(compact, sort_keys=True), flush=True)
    return summary["success"]


class LogTee:
    def __init__(self, terminal, log):
        self.terminal, self.log = terminal, log

    def write(self, value):
        self.terminal.write(value)
        self.log.write(value)
        return len(value)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "pilot", "download", "summary"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT)
    parser.add_argument("--lifecycle-dir", type=Path, default=LEDGER)
    parser.add_argument("--max-mib", type=float, required=True)
    args = parser.parse_args()
    if not 2 <= args.max_mib <= 1024:
        parser.error("--max-mib must be between2 and1024")
    log_path = ROOT / "reports/acquisition" / ("cmc_weekly_" + args.action + "_20261118.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    print("Log:", log_path, flush=True)
    exit_code = 1
    with log_path.open("a", encoding="utf-8") as log:
        with redirect_stdout(LogTee(sys.stdout, log)), redirect_stderr(LogTee(sys.stderr, log)):
            print("Output:", args.output_root, flush=True)
            try:
                with exclusive_run(args.output_root / ".collect.lock"):
                    exit_code = 0 if run(args) else 1
            except Exception:
                traceback.print_exc()
    raise SystemExit(exit_code)
