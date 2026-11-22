"""Bounded QTUM funding observation recovery and DEFI/LEND episode evidence."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from audit_history_extension import SOURCE, check_file
from check_identity_followup import capture
from collect_cmc_weekly import LogTee, checked_source
from review_contract_identity import article_text

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/early_cases_20261119.json"
OUTPUT = ROOT / "data/interim/usdm_universe/early_cases_20261119"
REVIEW = OUTPUT / "review_002"
START, END = 1580515200000, 1583020800000


def stamp(text):
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise ValueError("timezone required")
    return int(value.astimezone(UTC).timestamp() * 1000)


def decimal(text):
    if not isinstance(text, str):
        raise ValueError("decimal source string required")
    value = Decimal(text)
    if not value.is_finite():
        raise ValueError("non-finite source decimal")
    return value


def parse_funding(payload):
    if not isinstance(payload, list) or len(payload) >= 1000:
        raise ValueError("invalid or saturated funding response; completeness unproven")
    rows, times = [], []
    for item in payload:
        timestamp = item["fundingTime"]
        if (
            item["symbol"] != "QTUMUSDT"
            or type(timestamp) is not int
            or not START <= timestamp <= END
        ):
            raise ValueError("funding identity/bounds mismatch")
        decimal(item["fundingRate"])
        mark = item.get("markPrice")
        if mark not in (None, "") and decimal(mark) <= 0:
            raise ValueError("mark price must be positive")
        interval = item.get("fundingIntervalHours")
        if interval is not None and (type(interval) is not int or interval <= 0):
            raise ValueError("invalid reported interval")
        rows.append(
            {
                "instrument_id": "QTUMUSDT",
                "event_timestamp_ms": timestamp,
                "funding_rate_raw": item["fundingRate"],
                "mark_price_raw": mark,
                "reported_funding_interval_hours": interval,
                "rate_type_raw": item.get("rateType"),
                "available_at": None,
                "funding_payment_proven": False,
            }
        )
        times.append(timestamp)
    if times != sorted(set(times)):
        raise ValueError("funding timestamps duplicated or unordered")
    return rows


def overlap_check(rows, archive):
    observed = next((r for r in rows if r["event_timestamp_ms"] == END), None)
    baseline = next((r for r in archive if r["event_ms"] == END), None)
    return {
        "timestamp_ms": END,
        "api_event_present": observed is not None,
        "archive_event_present": baseline is not None,
        "rate_matches": bool(
            observed
            and baseline
            and decimal(observed["funding_rate_raw"]) == decimal(baseline["rate_raw"])
        ),
    }


def normalized(text):
    return re.sub(r"\s+", " ", html.unescape(text.replace("\\/", "/"))).casefold()


def verified_article(body, code, fragments):
    article, text = article_text(body, code)
    missing = [part for part in fragments if normalized(part) not in normalized(text)]
    return {
        "title": article["title"],
        "article_code": code,
        "clauses_verified": not missing,
        "missing_fragments": missing,
        "cms_release_date_raw": article.get("releaseDate"),
        "historical_content_version_proven": False,
        "causal_available_at": None,
    }, text


def capture_once():
    """Freeze this bounded capture, including202/other terminal failure evidence."""
    path = OUTPUT / "capture_summary.json"
    if not path.exists():
        capture(CONFIG, OUTPUT)
        return read_json(path), False
    summary = read_json(path)
    if summary["config_sha256"] != digest(CONFIG.read_bytes()):
        raise ValueError("capture configuration changed")
    for path in (OUTPUT / "raw/attempts").rglob("*.json"):
        metadata = read_json(path)
        body = path.with_suffix(".raw").read_bytes()
        if digest(body) != metadata["sha256"] or len(body) != metadata["bytes"]:
            raise ValueError("failed-source evidence integrity failure")
    return summary, True


def run():
    config_body = CONFIG.read_bytes()
    config = json.loads(config_body)
    binding = {
        "config_sha256": digest(config_body),
        "script_sha256": digest(Path(__file__).read_bytes()),
        "dependencies": {
            name: digest((ROOT / "scripts" / name).read_bytes())
            for name in (
                "check_identity_followup.py",
                "collect_cmc_weekly.py",
                "review_contract_identity.py",
                "audit_history_extension.py",
                "acquire_usdm_universe.py",
            )
        },
    }
    with exclusive_run(OUTPUT / ".cases.lock"):
        bind_run(OUTPUT / "source_contract", {"config_sha256": digest(config_body)})
        capture_summary, reused_capture = capture_once()
        sources = {}
        for source in config["sources"]:
            found = checked_source(OUTPUT, source["id"], source["url"])
            if found is not None:
                sources[source["id"]] = found
        binding["capture_summary_sha256"] = digest((OUTPUT / "capture_summary.json").read_bytes())
        binding["captured_source_hashes"] = {
            key: value[1]["sha256"] for key, value in sources.items()
        }
        binding["failed_attempt_hashes"] = {
            str(path.relative_to(OUTPUT)).replace("\\", "/"): digest(path.read_bytes())
            for path in sorted((OUTPUT / "raw/attempts").rglob("*.json"))
        }
        bind_run(REVIEW, binding)
        facts, issues = {}, []
        clauses = {
            "defi_launch": (
                "ebee6da5df3946519fdb9ab27706d1a4",
                ["2020/08/28 7:00 AM (UTC)", "not the ticker of a separate token"],
            ),
            "lend_settlement": (
                "17595222999545348c8acdd5dc41c00a",
                [
                    "2020/10/10 0:00 AM (UTC)",
                    "settling all LEND/USDT perpetual contract positions",
                    "2020/10/16 7:00 AM (UTC)",
                    "100 LEND = 1 AAVE",
                ],
            ),
        }
        for label, (code, fragments) in clauses.items():
            if label not in sources:
                issues.append(label + ": source unavailable")
                continue
            facts[label], text = verified_article(sources[label][0], code, fragments)
            facts[label]["source_sha256"] = sources[label][1]["sha256"]
            (REVIEW / (label + ".txt")).write_text(text, encoding="utf-8", newline="\n")
            if not facts[label]["clauses_verified"]:
                issues.append(label + ": expected clauses not verified")
        qtum_launch_verified = False
        if "qtum_launch" in sources:
            text = normalized(sources["qtum_launch"][0].decode("utf-8"))
            qtum_launch_verified = (
                all(term in text for term in ("2020/02/20", "08:00", "qtum"))
                and "this article does not exist" not in text
            )
        facts["qtum_launch"] = {
            "clauses_verified": qtum_launch_verified,
            "historical_content_version_proven": False,
            "causal_available_at": None,
        }
        if not qtum_launch_verified:
            issues.append("qtum_launch: exact dated clause not locally verified")
        february, overlap = [], {"rate_matches": False}
        if "qtum_funding" in sources:
            rows = parse_funding(json.loads(sources["qtum_funding"][0]))
            for row in rows:
                row.update(
                    source_sha256=sources["qtum_funding"][1]["sha256"],
                    source_url=sources["qtum_funding"][1]["url"],
                )
            plan_body = (SOURCE / "inventory/download_plan.json").read_bytes()
            if (
                digest(plan_body)
                != read_json(SOURCE / "inventory/summary.json")["plan_hashes"]["download_plan.json"]
            ):
                raise ValueError("early archive plan hash changed")
            planned = next(
                r
                for r in json.loads(plan_body)["files"]
                if (r["symbol"], r["kind"], r["month"]) == ("QTUMUSDT", "funding", "2020-03")
            )
            archive, _ = check_file(planned, REVIEW / "overlap_archive_audit")
            overlap = overlap_check(rows, archive["funding_events"])
            overlap["archive_report_sha256"] = archive["report_sha256"]
            if not overlap["rate_matches"]:
                issues.append("QTUM March1 boundary overlap missing or different")
            february = [r for r in rows if r["event_timestamp_ms"] < END]
            for row in february:
                row["before_proposed_launch"] = row["event_timestamp_ms"] < stamp(
                    config["events"]["qtum_launch"]
                )
                row["launch_clause_locally_verified"] = qtum_launch_verified
            if not february:
                issues.append("QTUM February observations not recovered")
        else:
            issues.append("qtum_funding: source unavailable")
        decisions = []
        if facts.get("defi_launch", {}).get("clauses_verified"):
            decisions.append(
                {
                    "instrument_id": "DEFIUSDT",
                    "scope_from": config["events"]["defi_launch"],
                    "scope_to_exclusive": "2021-01-01T00:00:00+00:00",
                    "known_asset_class": "composite_index_not_standalone_token",
                    "single_token_size_join_allowed": False,
                    "prelaunch_funding_payments_allowed": False,
                    "reason": "official index contract identity and launch; do not map to same-ticker token",
                }
            )
        if facts.get("lend_settlement", {}).get("clauses_verified"):
            decisions.append(
                {
                    "instrument_id": "LENDUSDT",
                    "scope_from": config["events"]["lend_settlement"],
                    "scope_to_exclusive": "2021-01-01T00:00:00+00:00",
                    "new_orders_or_postsettlement_funding_allowed": False,
                    "successor_instrument": "AAVEUSDT",
                    "successor_launch": config["events"]["aave_launch"],
                    "automatic_price_or_history_splice_allowed": False,
                    "reason": "official futures settlement; spot100:1 token swap does not splice contracts",
                }
            )
        write_json(REVIEW / "facts.json", facts)
        write_json(REVIEW / "qtum_february_observations.json", february)
        write_json(REVIEW / "march_overlap.json", overlap)
        write_json(
            REVIEW / "decisions.json",
            {
                "scope": config["scope"],
                "rules": decisions,
                "integrated_into_old_releases": False,
                "ex_post_review_only_not_causal_universe": True,
            },
        )
        result = {
            "success": not issues,
            "issues": issues,
            "capture_success": capture_summary["success"],
            "verified_sources": len(sources),
            "source_http_requests_this_run": 0
            if reused_capture
            else capture_summary["http_requests"],
            "terminal_capture_reused_without_retry": reused_capture,
            "qtum_february_observations": len(february),
            "qtum_first_event_ms": february[0]["event_timestamp_ms"] if february else None,
            "qtum_last_event_ms": february[-1]["event_timestamp_ms"] if february else None,
            "qtum_february_missing_event_mark_prices": sum(
                r["mark_price_raw"] in (None, "") for r in february
            ),
            "qtum_february_missing_reported_interval": sum(
                r["reported_funding_interval_hours"] is None for r in february
            ),
            "qtum_observations_before_proposed_launch": sum(
                r["before_proposed_launch"] for r in february
            ),
            "march_overlap_rate_matches": overlap["rate_matches"],
            "early_episode_rules": len(decisions),
            "funding_cashflows_verified": False,
            "historical_eligible_universe_ready": False,
            "old_releases_modified": False,
            "OOS_performance_inspected": False,
        }
        write_json(REVIEW / "summary.json", result)
        print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "summary"))
    args = parser.parse_args()
    if args.action == "summary":
        print(json.dumps(read_json(REVIEW / "summary.json"), sort_keys=True))
        return
    log = ROOT / "reports/acquisition/early_cases_20261119.log"
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
