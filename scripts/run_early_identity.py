"""One-pass, registry-driven identity processing for all81 early contracts."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
import time
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import check_early_identity_batch as batch
import check_early_identity_batch3 as batch3
import followup_early_identities as followup
import inventory_early_size as inventory
import verify_early_size_identities as identity
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from collect_cmc_weekly import Downloader, LogTee, checked_source

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "config/early_identity_remaining_004_20261119.json"


class TokenLinks(HTMLParser):
    """Collect real anchor captions; script strings are never parsed as links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.active, self.caption = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.active = dict(attrs).get("href")
            self.caption = []

    def handle_data(self, value):
        if self.active is not None:
            self.caption.append(value)

    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            self.links.append((self.active, " ".join("".join(self.caption).split())))
            self.active, self.caption = None, []


def contract_link(body, expected, caption):
    parser = TokenLinks()
    parser.feed(body.decode("utf-8"))
    for href, text in parser.links:
        url = urlsplit(href)
        if (
            url.scheme == "https"
            and url.netloc == "etherscan.io"
            and url.path.casefold() == "/token/" + expected.casefold()
            and not url.query
            and not url.fragment
            and text.casefold() == caption.casefold()
        ):
            return True, {
                "href": href,
                "anchor_text": text,
                "historical_content_version_proven": False,
            }
    return False, {"error": "exact Ethereum token anchor not found"}


def repo_path(value):
    path = (ROOT / value).resolve()
    path.relative_to(ROOT.resolve())
    return path


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def source_specs(plan):
    result = {}
    for item in plan["sources"]:
        spec = dict(item)
        if "article_code" in spec:
            spec["url"] = (
                "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode="
                + spec["article_code"]
            )
        if spec["id"] in result or not re.fullmatch(r"[A-Za-z0-9_-]+", spec["id"]):
            raise ValueError("duplicate/unsafe source ID")
        result[spec["id"]] = spec
    return result


def validate_extra_plan(plan):
    labels = set(source_specs(plan))
    symbols = [asset["instrument_id"] for asset in plan["assets"]]
    if len(symbols) != len(set(symbols)):
        raise ValueError("duplicate additional instrument")
    if len(labels) > 64:
        raise ValueError("additional source budget exceeded")
    for asset in plan["assets"]:
        if not all(
            asset.get(key) in labels for key in ("provider", "name_source", "future_source")
        ):
            raise ValueError("additional case has missing source references")
        for key in ("name_terms", "future_terms"):
            terms = asset.get(key)
            if not terms or not all(isinstance(term, str) and term.strip() for term in terms):
                raise ValueError("additional case needs explicit nonempty evidence terms")
        if not (asset.get("native_asset_expected") or asset.get("ethereum_contract")):
            raise ValueError("additional case needs token/native classification")
        if "ethereum_contract" in asset and (
            not re.fullmatch(r"0x[0-9a-fA-F]{40}", asset["ethereum_contract"])
            or asset.get("contract_source") not in labels
        ):
            raise ValueError("additional token needs exact address and source")
        if "contract_link_evidence" in asset and (
            "ethereum_contract" not in asset
            or not asset["contract_link_evidence"].get("anchor_text", "").strip()
            or not asset["contract_link_evidence"].get("document_host")
            or urlsplit(source_specs(plan)[asset["contract_source"]]["url"]).hostname
            != asset["contract_link_evidence"]["document_host"]
        ):
            raise ValueError("contract link evidence needs an address and caption")
        gates = {
            "historical_identity",
            "provider_identity",
            "venue_name",
            "venue_futures",
            "token_contract",
        }
        for assertion in asset.get("extra_assertions", []):
            if (
                assertion.get("source") not in labels
                or not assertion.get("gate")
                or assertion["gate"] in gates
                or not assertion.get("terms")
                or not all(isinstance(t, str) and t.strip() for t in assertion["terms"])
            ):
                raise ValueError("invalid additional evidence assertion")
            gates.add(assertion["gate"])
        if "provider_symbols" in asset:
            aliases = asset["provider_symbols"]
            if (
                not aliases
                or asset["symbol"] not in aliases
                or not all(isinstance(s, str) and s.strip() for s in aliases)
                or asset.get("provider_symbol_migration_gate")
                not in gates
                - {
                    "historical_identity",
                    "provider_identity",
                    "venue_name",
                    "venue_futures",
                    "token_contract",
                }
            ):
                raise ValueError("provider symbol aliases need a separate migration gate")
        start = datetime.fromisoformat(asset["scope_from"])
        end = datetime.fromisoformat(asset.get("scope_to_exclusive", "2021-01-01T00:00:00+00:00"))
        if (
            start.tzinfo is None
            or end.tzinfo is None
            or not (
                "2020-01-01" <= start.isoformat()[:10] < "2021-01-01"
                and start < end
                and end <= datetime.fromisoformat("2021-01-01T00:00:00+00:00")
            )
        ):
            raise ValueError("additional case outside the2020 review window")


def select_extra_plan(plan, symbols=None):
    """Prune HTTP dependencies as well as cases for a genuine small pilot."""
    if symbols is None:
        return plan
    selected = copy.deepcopy(plan)
    selected["assets"] = [a for a in plan["assets"] if a["instrument_id"] in symbols]
    needed = set()
    for asset in selected["assets"]:
        needed.update(asset[k] for k in ("provider", "name_source", "future_source"))
        if "contract_source" in asset:
            needed.add(asset["contract_source"])
        needed.update(a["source"] for a in asset.get("extra_assertions", []))
    selected["sources"] = [s for s in plan["sources"] if s["id"] in needed]
    return selected


def provider_labels_match(asset, current):
    if "provider_symbols" not in asset:
        return batch3.provider_labels_match(asset, current)
    return (
        current["id"] == asset["vendor_asset_id"]
        and current["symbol"] in asset["provider_symbols"]
        and current["name"].casefold()
        in {n.casefold() for n in asset.get("provider_names", [asset["name"]])}
    )


def verify_attempts(root, failed_labels=()):
    hashes, labels = {}, set()
    for path in (root / "raw/attempts").rglob("*.json"):
        meta = read_json(path)
        body = path.with_suffix(".raw").read_bytes()
        if len(body) != meta["bytes"] or digest(body) != meta["sha256"]:
            raise ValueError("failed-source body integrity mismatch")
        hashes[path.relative_to(root).as_posix()] = digest(path.read_bytes())
        labels.add(path.parent.name)
    if set(failed_labels) - labels:
        raise ValueError("missing terminal-failure evidence")
    return hashes


def load_review(spec, historical_hashes, early_hashes):
    config_path, root = repo_path(spec["config"]), repo_path(spec["root"])
    review = root / spec["review"]
    config, binding = read_json(config_path), read_json(review / "run_config.json")
    if digest(config_path.read_bytes()) != binding["config_sha256"]:
        raise ValueError("registered source configuration changed")
    if digest((ROOT / "scripts" / spec["tool"]).read_bytes()) != binding["script_sha256"]:
        raise ValueError("frozen review tool changed")
    for name, expected in binding["dependencies"].items():
        if digest((ROOT / "scripts" / name).read_bytes()) != expected:
            raise ValueError("frozen dependency changed: " + name)
    if "historical_hashes" in binding and binding["historical_hashes"] != historical_hashes:
        raise ValueError("historical snapshot binding differs")
    for key, value in early_hashes.items():
        if key in binding and binding[key] != value:
            raise ValueError("daily panel binding differs")
    capture_path = root / "capture_summary.json"
    if digest(capture_path.read_bytes()) != binding["capture_summary_sha256"]:
        raise ValueError("frozen capture summary changed")
    capture = read_json(capture_path)
    failed = [item["id"] for item in capture["failures"]]
    attempts = verify_attempts(root, failed)
    specs, found = source_specs(config), {}
    for label, source in specs.items():
        item = checked_source(root, label, source["url"])
        if item is not None:
            found[label] = item
    expected = binding.get("captured_sources", binding.get("source_hashes"))
    if {k: v[1]["sha256"] for k, v in found.items()} != expected:
        raise ValueError("frozen source set differs")
    return {
        "config": config,
        "root": root,
        "review": review,
        "binding": binding,
        "specs": specs,
        "sources": found,
        "attempts": attempts,
        "artifact_hashes": {p.name: digest(p.read_bytes()) for p in review.glob("*.json")},
    }


def evaluate_asset(asset, sources, specs, historical, panel, end, constrained=False):
    ok, history_report = batch.historical_check(asset, historical)
    proof = {
        "historical_identity": ok,
        "provider_identity": False,
        "venue_name": False,
        "venue_futures": False,
        "token_contract": True,
    }
    report = {"history": history_report}
    current = None
    if asset["provider"] in sources:
        try:
            current = identity.provider(sources[asset["provider"]][0], asset["vendor_asset_id"])
            proof["provider_identity"] = provider_labels_match(asset, current)
        except (ValueError, KeyError, TypeError) as exc:
            report["provider_error"] = str(exc)
    for gate, label, terms in (
        ("venue_name", asset["name_source"], asset["name_terms"]),
        ("venue_futures", asset["future_source"], asset["future_terms"]),
    ):
        proof[gate], report[gate] = batch.source_terms(label, terms, sources, specs)
    for assertion in asset.get("extra_assertions", []):
        gate = assertion["gate"]
        if gate in proof:
            raise ValueError("extra assertion cannot replace a required gate")
        proof[gate], report[gate] = batch.source_terms(
            assertion["source"], assertion["terms"], sources, specs
        )
    if "provider_symbols" in asset:
        proof["provider_identity"] &= proof.get(asset["provider_symbol_migration_gate"], False)
    if "ethereum_contract" in asset:
        expected = asset["ethereum_contract"]
        origin, report["contract_origin"] = batch.source_terms(
            asset.get("contract_source", "link_contract"), [expected], sources, specs
        )
        if "contract_link_evidence" in asset:
            label = asset["contract_source"]
            evidence = asset["contract_link_evidence"]
            origin = False
            if (
                label in sources
                and urlsplit(specs[label]["url"]).hostname == evidence["document_host"]
            ):
                origin, report["contract_origin"] = contract_link(
                    sources[label][0], expected, evidence["anchor_text"]
                )
        proof["token_contract"] = (
            current is not None and identity.ethereum_contract(current, expected) and origin
        )
    factory = batch3.constrained_rule if constrained else batch.rule
    result = factory(asset, proof, end)
    start = datetime.fromisoformat(result["scope_from"]).timestamp() * 1000
    stop = datetime.fromisoformat(result["scope_to_exclusive"]).timestamp() * 1000
    result["price_history_candidate_weeks_in_scope"] = sum(
        start <= stamp < stop and row["price_history_diagnostic_candidate"]
        for stamp, row in panel[asset["instrument_id"]].items()
    )
    return result, report


def verify_base(base, supplement, historical):
    # The supplement freezes hashes of all predecessor proof/decision artifacts.
    for name, expected in supplement["binding"]["prior_artifact_hashes"].items():
        if digest((base["review"] / name).read_bytes()) != expected:
            raise ValueError("base proof artifact changed")
    proof = read_json(base["review"] / "proof_checks.json")
    original = identity.decisions(proof)
    if original != read_json(base["review"] / "mapping_decisions.json"):
        raise ValueError("base decisions do not reproduce")
    extra = read_json(supplement["review"] / "proof_checks.json")
    rules = followup.supplemented_rules(original, extra)
    if rules != read_json(supplement["review"] / "mapping_decisions.json"):
        raise ValueError("supplement decisions do not reproduce")
    # Recheck the recovered IOTA alias against primary bodies and dated rows.
    current = identity.provider(base["sources"]["cmc_iota"][0], 1720)
    _, _, units = followup.article_check(supplement["sources"]["iota_units"][0], "115002193731", [])
    origin = identity.text(supplement["sources"]["iota_origin"][0])
    if not (
        current["id"] == 1720
        and identity.iota_unit_clause(units.encode())
        and "what was previously 1 miota will now simply be one iota" in origin
        and sum(
            r["vendor_asset_id"] == 1720 and r["symbol"] == "MIOTA" and r["name"] == "IOTA"
            for r in historical
        )
        == 54
    ):
        raise ValueError("IOTA recovery evidence differs")
    return rules


def register_rule(registry, result, provenance, assertion=None):
    symbol = result["instrument_id"]
    record = {
        "mapping": copy.deepcopy(result),
        "provenance": provenance,
        "rule_sha256": fingerprint(result),
    }
    if symbol in registry:
        old = registry[symbol]
        if (
            not assertion
            or assertion.get("replaces_rule_sha256") != old["rule_sha256"]
            or not assertion.get("replacement_reason")
        ):
            raise ValueError("duplicate case needs an explicit versioned replacement: " + symbol)
        record["superseded"] = old
    registry[symbol] = record


def verify_output_hashes(target, summary):
    for name, expected in summary["output_hashes"].items():
        if digest((target / name).read_bytes()) != expected:
            raise ValueError("derived report integrity mismatch: " + name)


def load_source_predecessor(spec, existing=None):
    version = spec["version"]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", version):
        raise ValueError("unsafe predecessor version")
    root = ROOT / "data/interim/early_identity_all" / version
    target = root / "full"
    hashes = {}
    for name in ("summary.json", "run_config.json"):
        hashes[name] = digest((target / name).read_bytes())
        if hashes[name] != spec["artifact_hashes"][name]:
            raise ValueError("predecessor binding changed")
    summary, binding = read_json(target / "summary.json"), read_json(target / "run_config.json")
    if not summary["success"] or not summary["full_scope"]:
        raise ValueError("predecessor must be a successful full processing run")
    verify_output_hashes(target, summary)
    plan_path = repo_path(spec["plan"])
    if digest(plan_path.read_bytes()) != binding["plan_sha256"]:
        raise ValueError("predecessor source plan changed")
    specs = source_specs(read_json(plan_path)["additional_plan"])
    outcomes = read_json(target / "additional_sources.json")
    if outcomes != binding["additional_outcomes"]:
        raise ValueError("predecessor outcomes differ from binding")
    available, frozen = {}, set()
    for label, outcome in outcomes.items():
        url = specs[label]["url"]
        if outcome["state"] == "available":
            item = (existing or {}).get(url) or checked_source(
                root / "additional_cache", digest(url.encode()), url
            )
            if item is None or item[1] != outcome["source"]:
                raise ValueError("predecessor source missing or metadata differs")
            available[url] = item
        elif outcome["state"] == "terminal_failure":
            key = digest(url.encode())
            checkpoint = read_json(root / "additional_cache/terminal" / (key + ".json"))
            actual = verify_attempts(
                root / "additional_cache", [key] if checkpoint["attempt_hashes"] else []
            )
            if (
                checkpoint["url"] != url
                or checkpoint["error"] != outcome["error"]
                or any(actual.get(p) != h for p, h in checkpoint["attempt_hashes"].items())
            ):
                raise ValueError("predecessor terminal failure changed")
            frozen.add(url)
    return available, frozen, read_json(target / "asset_review.json"), hashes


def preserve_prior_passes(previous, rows):
    current = {r["instrument_id"]: r for r in rows}
    for old in previous:
        if old["identity_status"] == "corroborated_identity" and (
            old["mapping_record"]["mapping"]
            != current[old["instrument_id"]]["mapping_record"]["mapping"]
        ):
            raise ValueError("previously corroborated rule changed: " + old["instrument_id"])


def row_status(item, record):
    result = copy.deepcopy(item)
    result["price_history_state"] = (
        "at_least_one_candidate_week"
        if item["price_history_candidate_weeks"]
        else "no_candidate_week"
    )
    result["strict_strategy_eligible"] = False
    result["mapping_record"] = record
    if item["instrument_id"] == "DEFIUSDT":
        result["identity_status"], result["missing_requirements"] = "composite_index", []
    elif record:
        rule = record["mapping"]
        passed = rule["size_identity_join_allowed"]
        result["identity_status"] = (
            "corroborated_identity" if passed else "pending_registered_evidence"
        )
        result["missing_requirements"] = (
            [] if passed else rule.get("pending_gates", ["registered_identity_evidence_incomplete"])
        )
    else:
        result["identity_status"] = "needs_source_assertions"
        result["missing_requirements"] = [
            "provider_identity",
            "official_name_source",
            "futures_scope",
            "token_or_native_phase_review",
        ]
        if item["literal_IDs_change_or_multiple"]:
            result["missing_requirements"].append("episode_identity_review")
    return result


def additional_sources(plan, output, fetch, available, frozen_urls):
    specs = source_specs(plan)
    allowed = set(
        plan.get(
            "allowed_hosts",
            ["www.binance.com", "coinmarketcap.com", "basicattentiontoken.org", "docs.chain.link"],
        )
    )
    root = output / "additional_cache"
    downloader = Downloader(root, min(plan["max_raw_bytes"], 32 * 1024**2))
    found, outcomes = {}, {}
    for label, spec in specs.items():
        url = spec["url"]
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname not in allowed
            or parts.username
            or parts.password
        ):
            raise ValueError("unregistered public source host")
        key = digest(url.encode())
        terminal = root / "terminal" / (key + ".json")
        item = available.get(url) or checked_source(root, key, url)
        if item is not None:
            found[label] = item
            outcomes[label] = {"state": "available", "source": item[1]}
            continue
        if terminal.exists():
            checkpoint = read_json(terminal)
            actual = verify_attempts(root, [key] if checkpoint["attempt_hashes"] else [])
            if checkpoint["url"] != url or any(
                actual.get(p) != h for p, h in checkpoint["attempt_hashes"].items()
            ):
                raise ValueError("terminal source checkpoint changed")
            outcomes[label] = {"state": "terminal_failure", "error": checkpoint["error"]}
            continue
        if url in frozen_urls or not fetch or (root / "access_pause.json").exists():
            outcomes[label] = {
                "state": "not_requested",
                "reason": "frozen_prior_failure"
                if url in frozen_urls
                else "fetch_disabled_or_paused",
            }
            continue
        try:
            body, meta, _ = downloader.get(key, url)
            item = (body, meta, True)
            found[label], available[url] = item, item
            outcomes[label] = {"state": "available", "source": meta}
        except Exception as exc:
            hashes = verify_attempts(root)
            selected = {p: h for p, h in hashes.items() if Path(p).parent.name == key}
            write_json(terminal, {"url": url, "error": str(exc), "attempt_hashes": selected})
            outcomes[label] = {"state": "terminal_failure", "error": str(exc)}
        if downloader.requests and downloader.requests % 10 == 0:
            print(
                f"additional sources: {len(outcomes)}/{len(specs)}; HTTP={downloader.requests}",
                flush=True,
            )
    return found, specs, outcomes, downloader.requests


def run(args):
    started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.version):
        raise ValueError("unsafe output version")
    plan_path = repo_path(args.plan)
    plan = read_json(plan_path)
    validate_extra_plan(plan["additional_plan"])
    output = ROOT / "data/interim/early_identity_all" / args.version
    mode = "pilot" if args.pilot else "full"
    with exclusive_run(output / ".all.lock"):
        dependencies = [
            "check_early_identity_batch.py",
            "check_early_identity_batch2.py",
            "check_early_identity_batch3.py",
            "followup_early_identities.py",
            "verify_early_size_identities.py",
            "inventory_early_size.py",
            "collect_cmc_weekly.py",
            "acquire_usdm_universe.py",
            "check_early_cases.py",
            "review_contract_identity.py",
            "check_identity_followup.py",
        ]
        contract = {
            "plan_sha256": digest(plan_path.read_bytes()),
            "script_sha256": digest(Path(__file__).read_bytes()),
            "dependencies": {
                name: digest((ROOT / "scripts" / name).read_bytes()) for name in dependencies
            },
        }
        bind_run(output / "contract", contract)
        _, historical_hashes = identity.historical_ids()
        captured = {
            label: read_json(inventory.OUTPUT / "full/partitions" / (label + ".json"))
            for label in inventory.dates()
        }
        historical = [r for rows in captured.values() for r in rows]
        panel, early_hashes = inventory.load_panel()
        _, queue = inventory.summarize(panel, captured, inventory.dates())
        if len(queue) != plan["expected_identifiers"] or queue != read_json(
            inventory.OUTPUT / "full/asset_review_queue.json"
        ):
            raise ValueError("original81-item inventory does not reproduce")
        contexts, registry, evidence = [], {}, {}
        for spec in plan["bundles"]:
            context = load_review(spec, historical_hashes, early_hashes)
            contexts.append(context)
            results = []
            for asset in context["config"]["assets"]:
                decision, proof = evaluate_asset(
                    asset,
                    context["sources"],
                    context["specs"],
                    historical,
                    panel,
                    context["config"]["scope_end_exclusive"],
                    spec["kind"] == "batch3",
                )
                results.append(decision)
                register_rule(registry, decision, spec["root"] + "/" + spec["review"])
                evidence[asset["instrument_id"]] = proof
            if results != read_json(context["review"] / "mapping_decisions.json"):
                raise ValueError("registered decisions do not reproduce: " + spec["root"])
        base = load_review(plan["base"], historical_hashes, early_hashes)
        supplement = load_review(plan["supplement"], historical_hashes, early_hashes)
        contexts.extend([base, supplement])
        for decision in verify_base(base, supplement, historical):
            register_rule(registry, decision, supplement["review"].relative_to(ROOT).as_posix())
        available, frozen_urls = {}, set()
        for context in contexts:
            for label, spec in context["specs"].items():
                if label in context["sources"]:
                    available.setdefault(spec["url"], context["sources"][label])
                else:
                    frozen_urls.add(spec["url"])
        previous_rows, predecessor_hashes = [], {}
        if "source_predecessor" in plan:
            inherited, failures, previous_rows, predecessor_hashes = load_source_predecessor(
                plan["source_predecessor"], available
            )
            available.update(inherited)
            frozen_urls.update(failures)
        extra = select_extra_plan(
            plan["additional_plan"], set(plan["pilot_symbols"]) if args.pilot else None
        )
        found, specs, outcomes, requests = additional_sources(
            extra, output, args.fetch, available, frozen_urls
        )
        for asset in extra["assets"]:
            if asset["instrument_id"] not in panel:
                raise ValueError("additional case outside81 identifiers")
            decision, proof = evaluate_asset(
                asset, found, specs, historical, panel, "2021-01-01T00:00:00+00:00", True
            )
            register_rule(registry, decision, "additional_plan", asset)
            evidence[asset["instrument_id"]] = proof
        rows = [
            row_status(item, registry.get(item["instrument_id"]))
            for item in sorted(
                queue, key=lambda r: (-r["price_history_candidate_weeks"], r["instrument_id"])
            )
        ]
        preserve_prior_passes(
            [
                r
                for r in previous_rows
                if not args.pilot or r["instrument_id"] in plan["pilot_symbols"]
            ],
            rows,
        )
        if args.pilot:
            rows = [r for r in rows if r["instrument_id"] in plan["pilot_symbols"]]
        binding = {
            **contract,
            **early_hashes,
            "historical_hashes": historical_hashes,
            "prior_reviews": {
                c["review"].relative_to(ROOT).as_posix(): c["artifact_hashes"] for c in contexts
            },
            "prior_failed_attempts": {
                c["root"].relative_to(ROOT).as_posix(): c["attempts"] for c in contexts
            },
            "additional_outcomes": outcomes,
            "source_predecessor_artifacts": predecessor_hashes,
            "mode": mode,
        }
        target = output / mode
        bind_run(target, binding)
        write_json(target / "asset_review.json", rows)
        write_json(target / "missing_evidence.json", [r for r in rows if r["missing_requirements"]])
        write_json(target / "evidence_checks.json", evidence)
        write_json(target / "additional_sources.json", outcomes)
        path = target / "asset_review.csv"
        temporary = path.with_suffix(".csv.part")
        with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "instrument_id",
                    "identity_status",
                    "price_history_candidate_weeks",
                    "price_history_state",
                    "missing_requirements",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        k: ";".join(row[k]) if isinstance(row[k], list) else row[k]
                        for k in writer.fieldnames
                    }
                )
        temporary.replace(path)
        counts = Counter(r["identity_status"] for r in rows)
        qualified = [r for r in rows if r["price_history_candidate_weeks"]]
        summary = {
            "success": True,
            "full_scope": not args.pilot,
            "identifiers_processed": len(rows),
            "identity_status_counts": dict(counts),
            "price_history_candidate_identifiers": len(qualified),
            "supported_price_history_identifiers": sum(
                r["identity_status"] == "corroborated_identity" for r in qualified
            ),
            "candidate_asset_weeks": sum(r["price_history_candidate_weeks"] for r in rows),
            "all_identity_checks_complete": not any(r["missing_requirements"] for r in rows),
            "source_http_requests_this_run": requests,
            "additional_cases_evaluated": len(extra["assets"]),
            "additional_sources_selected": len(specs),
            "additional_source_states": dict(Counter(v["state"] for v in outcomes.values())),
            "old_batch_runners_invoked": 0,
            "common_input_validation_passes": 1,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "historical_eligible_universe_ready": False,
            "canonical_joins_materialized": 0,
            "OOS_performance_inspected": False,
            "result_path": str(target / "asset_review.json"),
            "output_hashes": {
                name: digest((target / name).read_bytes())
                for name in (
                    "asset_review.json",
                    "missing_evidence.json",
                    "evidence_checks.json",
                    "additional_sources.json",
                    "asset_review.csv",
                )
            },
        }
        write_json(target / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "summary"))
    parser.add_argument("--plan", default=str(DEFAULT.relative_to(ROOT)))
    parser.add_argument("--version", default="v20261119_007")
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument(
        "--fetch", action="store_true", help="fetch only explicitly registered additional sources"
    )
    args = parser.parse_args()
    if args.action == "summary":
        if not re.fullmatch(r"[A-Za-z0-9_-]+", args.version):
            raise ValueError("unsafe output version")
        target = (
            ROOT
            / "data/interim/early_identity_all"
            / args.version
            / ("pilot" if args.pilot else "full")
        )
        summary = read_json(target / "summary.json")
        verify_output_hashes(target, summary)
        print(json.dumps(summary, sort_keys=True))
        return
    log = ROOT / "reports/acquisition" / ("early_identity_all_" + args.version + ".log")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.version):
        raise ValueError("unsafe output version")
    print("Log: " + str(log), flush=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    with (
        log.open("a", encoding="utf-8") as handle,
        redirect_stdout(LogTee(sys.stdout, handle)),
        redirect_stderr(LogTee(sys.stderr, handle)),
    ):
        run(args)


if __name__ == "__main__":
    main()
