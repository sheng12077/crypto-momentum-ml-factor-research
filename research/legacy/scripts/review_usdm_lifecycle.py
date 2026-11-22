"""Archive official announcement versions and build an ex-post review ledger."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from acquire_usdm_universe import digest, read_json, write_json


def text_nodes(node):
    if isinstance(node, dict):
        return ([node["text"]] if node.get("node") == "text" else []) + [
            text for child in node.get("child", []) for text in text_nodes(child)
        ]
    return []


def collect(source, directory):
    code = source["article_code"]
    if not re.fullmatch(r"[a-f0-9]{32}", code):
        raise ValueError("invalid official article code")
    target = directory / "sources" / (code + ".json")
    raw = target.with_suffix(".raw")
    if target.exists():
        result = read_json(target)
        if digest(raw.read_bytes()) != result["sha256"]:
            raise ValueError("cached announcement changed")
        return result
    url = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode="
        + code
    )
    request = urllib.request.Request(url, headers={"User-Agent": "research-data-audit/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(5 * 1024**2)
    payload = json.loads(body)
    if not payload.get("success") or not payload.get("data", {}).get("body"):
        raise ValueError("official CMS did not return an article")
    article = payload["data"]
    content = " ".join(text_nodes(json.loads(article["body"])))
    target.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(body)
    raw.with_suffix(".txt").write_text(content, encoding="utf-8")
    result = {
        "article_code": code,
        "title": article["title"],
        "source_url": source["url"],
        "retrieval_url": url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sha256": digest(body),
        "bytes": len(body),
        "cms_release_date_raw": article.get("releaseDate"),
        "historical_content_version_proven": False,
        "causal_available_at": None,
    }
    write_json(target, result)
    return result


def build(args):
    config = read_json(args.facts)
    sources, errors = {}, []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [
            (source, pool.submit(collect, source, args.output_dir)) for source in config["sources"]
        ]
        for source, job in jobs:
            try:
                sources[source["article_code"]] = job.result()
            except Exception as exc:
                errors.append({"article_code": source["article_code"], "error": str(exc)})
    events = []
    for event in config["events"]:
        code = event["article_code"]
        if code not in sources:
            continue
        article = json.loads((args.output_dir / "sources" / (code + ".raw")).read_bytes())["data"]
        text = " ".join(text_nodes(json.loads(article["body"])))
        absent = [
            term for term in event["evidence_terms"] if term.casefold() not in text.casefold()
        ]
        if absent:
            errors.append({"event_id": event["event_id"], "missing_evidence_terms": absent})
            continue
        stamp = datetime.fromisoformat(event["effective_at"])
        if stamp.utcoffset().total_seconds() != 0:
            raise ValueError("event must explicitly use UTC")
        events.append(
            {
                **event,
                "market_scope": "binance_usdm_perpetual",
                "fact_interpretation": "ex_post_only",
                "causal_available_at": None,
                "source": sources[code],
            }
        )
    quality = {r["symbol"]: r for r in read_json(args.audit_dir / "symbol_quality.json")}
    month_gaps = read_json(args.audit_dir / "review_rollup.json")["whole_month_interior_gaps"]
    # Keys in source audit are symbols, including instruments with multiple missing months.
    month_symbols = (
        {r["symbol"] for r in month_gaps} if isinstance(month_gaps, list) else set(month_gaps)
    )
    seven = {"AERGOUSDT", "CTKUSDT", "CVCUSDT", "CVXUSDT", "LITUSDT", "PUMPUSDT", "SLPUSDT"}
    ledger = []
    for identity in read_json(args.census_dir / "identity_ledger.json"):
        symbol = identity["instrument_id"]
        observed = quality[symbol]
        selected = [event for event in events if event["instrument_id"] == symbol]
        priorities = []
        if symbol in seven:
            priorities.append("remaining_mark_gap")
        if observed["funding_files_starting_after_last_positive_trade"]:
            priorities.append("funding_after_last_observed_activity")
        if symbol in month_symbols:
            priorities.append("missing_funding_months")
        ledger.append(
            {
                **identity,
                "review_priorities": priorities,
                "official_events": selected,
                "lifecycle_review_status": "partial_official_evidence"
                if selected
                else "unresolved",
                "known_identity_reuse": symbol in config["identity_reuse"],
                "identity_reuse_note": config["identity_reuse"].get(symbol),
                "first_positive_trade_bar_ex_post": observed["first_positive_trade_bar"],
                "last_positive_trade_bar_ex_post": observed["last_positive_trade_bar"],
                "funding_rows_after_last_activity_ex_post": observed["funding_rows_in_those_files"],
                "review_flags_ex_post": observed["review_flags"],
                "complete_lifecycle_verified": False,
                "historical_strategy_eligible": False,
                "unresolved": [
                    "full_episode_boundaries",
                    "historical_announcement_availability",
                    "terminal_settlement_price_and_cashflows",
                    "historical_contract_specifications",
                ],
            }
        )
    write_json(args.output_dir / "events.json", events)
    write_json(args.output_dir / "identity_ledger.json", ledger)
    priority = [r for r in ledger if r["review_priorities"]]
    summary = {
        "success": not errors,
        "identifiers": len(ledger),
        "official_sources": len(sources),
        "verified_events": len(events),
        "identifiers_with_official_events": sum(bool(r["official_events"]) for r in ledger),
        "priority_identifiers": len(priority),
        "priority_with_official_events": sum(bool(r["official_events"]) for r in priority),
        "known_identity_reuse": config["identity_reuse"],
        "full_lifecycle_verified": 0,
        "historical_eligible_universe_ready": False,
        "errors": errors,
        "facts_sha256": digest(args.facts.read_bytes()),
        "events_sha256": digest((args.output_dir / "events.json").read_bytes()),
        "ledger_sha256": digest((args.output_dir / "identity_ledger.json").read_bytes()),
    }
    write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return not errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("facts", "census-dir", "audit-dir", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    raise SystemExit(0 if build(parser.parse_args()) else 1)
