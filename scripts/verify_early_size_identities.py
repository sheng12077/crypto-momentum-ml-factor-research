"""Bounded provider/official evidence review;no canonical joins or trading approval."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from check_early_cases import verified_article
from check_identity_followup import parse_cmc_identity
from collect_cmc_weekly import Downloader, LogTee, checked_source, raw_bytes, write_source
from inventory_early_size import OUTPUT as INVENTORY
from inventory_early_size import dates

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/early_size_identity_20261119.json"
OUTPUT = ROOT / "data/interim/early_size_identity_20261119"
OLD_CASE = ROOT / "data/interim/usdm_universe/early_cases_20261119"
LIMIT = 32 * 1024**2


def text(body):
    value = html.unescape(body.decode("utf-8")).replace("\\/", "/")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).casefold()


def provider(body, expected_id):
    identity = parse_cmc_identity(body)
    if identity["id"] != expected_id:
        raise ValueError("provider ID mismatch;redirect/name cannot override historical identity")
    return identity


def ethereum_contract(identity, expected):
    return any(
        (row.get("contractPlatform") or "").casefold() == "ethereum"
        and (row.get("contractAddress") or "").casefold() == expected.casefold()
        for row in identity["contracts"]
    )


def iota_unit_clause(body):
    return "1iota=1miota" in re.sub(r"\s+", "", text(body))


def historical_ids():
    summary = read_json(INVENTORY / "full/summary.json")
    if (
        not summary["success"]
        or not summary["full_scope"]
        or summary["captured_snapshot_dates"] != 54
    ):
        raise ValueError("require complete historical Size inventory")
    rows, hashes = [], {}
    for label in dates():
        path = INVENTORY / "full/partitions" / (label + ".json")
        body = path.read_bytes()
        index = read_json(INVENTORY / "full/index" / (label + ".json"))
        source, metadata, _ = checked_source(
            INVENTORY, label, "https://coinmarketcap.com/historical/" + label + "/"
        )
        if digest(body) != index["parsed_sha256"] or digest(source) != index["source_sha256"]:
            raise ValueError("historical snapshot source/parsed integrity failure")
        parsed = json.loads(body)
        if len(parsed) != index["rows"]:
            raise ValueError("historical snapshot count mismatch")
        rows.extend(r for r in parsed if r["vendor_asset_id"] in (1720, 4113, 7083, 2239, 7278))
        hashes[label] = {"parsed": digest(body), "raw": metadata["sha256"]}
    return rows, hashes


def capture_sources(config):
    summary_path = OUTPUT / "capture_summary.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        if summary["config_sha256"] != digest(CONFIG.read_bytes()):
            raise ValueError("source contract changed")
        for path in (OUTPUT / "raw/attempts").rglob("*.json"):
            meta = read_json(path)
            body = path.with_suffix(".raw").read_bytes()
            if digest(body) != meta["sha256"] or len(body) != meta["bytes"]:
                raise ValueError("terminal failure evidence integrity failure")
        return summary, 0
    if (OUTPUT / "access_pause.json").exists():
        raise ValueError("access stopped;do not retry automatically")
    allowed = {
        "coinmarketcap.com",
        "www.binance.com",
        "blog.uniswap.org",
        "raw.githubusercontent.com",
    }
    specs = config["sources"]
    if len(specs) != 11 or len({s["id"] for s in specs}) != 11:
        raise ValueError("registered source budget changed")
    downloader = Downloader(OUTPUT, LIMIT)
    results, failures = [], []
    for spec in specs:
        if spec.get("reuse_early_case"):
            old = checked_source(OLD_CASE, spec["id"], spec["url"])
            if old is None:
                raise ValueError("required prior official evidence missing")
            write_source(OUTPUT, spec["id"], old[0], old[1])
    for spec in specs:
        url = urlsplit(spec["url"])
        if url.scheme != "https" or url.hostname not in allowed:
            raise ValueError("unexpected source host")
        if spec.get("reuse_early_case"):
            old = checked_source(OLD_CASE, spec["id"], spec["url"])
            if old is None:
                raise ValueError("required prior official evidence missing")
            write_source(OUTPUT, spec["id"], old[0], old[1])
        try:
            _, metadata, cached = downloader.get(spec["id"], spec["url"])
            results.append({"id": spec["id"], "source": metadata, "cache_hit": cached})
        except Exception as exc:
            failures.append({"id": spec["id"], "error": str(exc)})
            if (OUTPUT / "access_pause.json").exists():
                break
    summary = {
        "success": len(results) == len(specs),
        "requested_sources": len(specs),
        "results": results,
        "failures": failures,
        "http_requests": downloader.requests,
        "raw_bytes": raw_bytes(OUTPUT),
        "config_sha256": digest(CONFIG.read_bytes()),
    }
    write_json(summary_path, summary)
    return summary, downloader.requests


def decisions(proof):
    def rule(symbol, vendor, start, end, supported):
        return {
            "instrument_id": symbol,
            "vendor_asset_id": vendor,
            "scope_from": start,
            "scope_to_exclusive": end,
            "size_identity_join_allowed": bool(supported),
            "usd_market_cap_scale": "1",
            "price_or_history_splice_allowed": False,
            "full_contract_specifications_verified": False,
            "funding_cashflows_verified": False,
            "historical_publication_vintage_proven": False,
            "historical_strategy_eligible": False,
        }

    end = "2021-01-01T00:00:00+00:00"
    iota = rule(
        "IOTAUSDT",
        1720,
        "2020-01-01T00:00:00+00:00",
        end,
        all(
            proof.get(k, False)
            for k in ("iota_provider", "iota_history", "iota_project", "iota_units")
        ),
    )
    iota["scope_is_identity_not_contract_listing"] = True
    uni = rule("UNIUSDT", 7083, "2020-09-17T03:00:00+00:00", end, False)
    uni.update(
        asset_identity_supported=all(
            proof.get(k, False)
            for k in ("uni_provider", "uni_contract", "uni_origin", "uni_project", "uni_history")
        ),
        futures_specific_2020_link_verified=False,
        rejected_vendor_ids=[4113],
        reason="underlying identity separated;2020 futures-specific link/time not independently established",
    )
    aave_supported = all(
        proof.get(k, False)
        for k in (
            "aave_provider",
            "aave_contract",
            "aave_origin",
            "migration_notice",
            "aave_lend_history",
        )
    )
    lend = rule(
        "LENDUSDT", 2239, "2020-01-01T00:00:00+00:00", "2020-10-10T00:00:00+00:00", aave_supported
    )
    aave = rule("AAVEUSDT", 7278, "2020-10-16T07:00:00+00:00", end, aave_supported)
    lend["reject_current_aave_url_as_old_id"] = 7278
    aave["reject_old_lend_id"] = 2239
    return [iota, uni, lend, aave]


def resolve_vendor(rules, instrument, reference):
    for rule in rules:
        if (
            rule["instrument_id"] == instrument
            and rule["size_identity_join_allowed"]
            and datetime.fromisoformat(rule["scope_from"])
            <= reference
            < datetime.fromisoformat(rule["scope_to_exclusive"])
        ):
            if (
                Decimal(rule["usd_market_cap_scale"]) != 1
                or rule["price_or_history_splice_allowed"]
            ):
                raise ValueError("identity mapping cannot rescale cap or splice history")
            return rule["vendor_asset_id"]
    return None


def run():
    config_body = CONFIG.read_bytes()
    config = json.loads(config_body)
    with exclusive_run(OUTPUT / ".identity.lock"):
        bind_run(OUTPUT / "source_contract", {"config_sha256": digest(config_body)})
        capture, requests = capture_sources(config)
        historical, historical_hashes = historical_ids()
        sources, identities, issues = {}, {}, []
        for spec in config["sources"]:
            checked = checked_source(OUTPUT, spec["id"], spec["url"])
            if checked is not None:
                sources[spec["id"]] = checked
        for label, expected in config["expected_provider_ids"].items():
            if label not in sources:
                issues.append(label + ":missing source")
                continue
            try:
                identities[label] = provider(sources[label][0], expected)
            except Exception as exc:
                issues.append(label + ":" + str(exc))

        def contains(label, fragments):
            return label in sources and all(
                part.casefold() in text(sources[label][0]) for part in fragments
            )

        proof = {
            "iota_provider": "cmc_iota" in identities,
            "iota_history": sum(
                r["vendor_asset_id"] == 1720 and r["name"] == "IOTA" and r["symbol"] == "MIOTA"
                for r in historical
            )
            == 54,
            "iota_project": contains("iota_project", ["IOTA (MIOTA)", "iota.org"]),
            "iota_units": "iota_units" in sources and iota_unit_clause(sources["iota_units"][0]),
            "uni_provider": "cmc_uni" in identities,
            "uni_contract": "cmc_uni" in identities
            and ethereum_contract(identities["cmc_uni"], config["expected_uni_ethereum_contract"]),
            "uni_origin": contains(
                "uni_origin", ["UNI contract address", config["expected_uni_ethereum_contract"]]
            ),
            "uni_project": contains("uni_project", ["Uniswap (UNI)", "ERC-20"]),
            "uni_history": any(
                r["vendor_asset_id"] == 7083 and r["name"] == "Uniswap" for r in historical
            )
            and any(r["vendor_asset_id"] == 4113 and r["name"] == "UNI COIN" for r in historical),
            "aave_provider": "cmc_aave" in identities,
            "aave_contract": "cmc_aave" in identities
            and ethereum_contract(
                identities["cmc_aave"], config["expected_aave_ethereum_contract"]
            ),
            "aave_origin": contains("aave_origin", ["100 LEND per 1 AAVE"]),
            "aave_lend_history": any(
                r["vendor_asset_id"] == 2239 and r["symbol"] == "LEND" and r["name"] == "Aave"
                for r in historical
            )
            and any(
                r["vendor_asset_id"] == 7278 and r["symbol"] == "AAVE" and r["name"] == "Aave"
                for r in historical
            ),
            "migration_notice": False,
        }
        if "lend_settlement" in sources:
            notice, _ = verified_article(
                sources["lend_settlement"][0],
                "17595222999545348c8acdd5dc41c00a",
                [
                    "2020/10/10 0:00 AM (UTC)",
                    "settling all LEND/USDT perpetual contract positions",
                    "2020/10/16 7:00 AM (UTC)",
                ],
            )
            proof["migration_notice"] = notice["clauses_verified"]
        rules = decisions(proof)
        binding = {
            "config_sha256": digest(config_body),
            "script_sha256": digest(Path(__file__).read_bytes()),
            "source_hashes": {label: value[1]["sha256"] for label, value in sources.items()},
            "capture_summary_sha256": digest((OUTPUT / "capture_summary.json").read_bytes()),
            "historical_hashes": historical_hashes,
            "dependencies": {
                name: digest((ROOT / "scripts" / name).read_bytes())
                for name in (
                    "check_identity_followup.py",
                    "collect_cmc_weekly.py",
                    "review_contract_identity.py",
                    "check_early_cases.py",
                    "acquire_usdm_universe.py",
                )
            },
        }
        target = OUTPUT / "review_001"
        bind_run(target, binding)
        write_json(target / "provider_identities.json", identities)
        write_json(target / "proof_checks.json", proof)
        write_json(target / "mapping_decisions.json", rules)
        named = read_json(INVENTORY / "full/asset_review_queue.json")
        gaps = next(r for r in named if r["instrument_id"] == "IOTAUSDT")[
            "missing_size_in_price_history_weeks"
        ]
        result = {
            "review_completed": True,
            "source_capture_complete": capture["success"],
            "issues": issues,
            "source_http_requests_this_run": requests,
            "verified_sources": len(sources),
            "verified_2020_size_identity_rules": sum(
                r["size_identity_join_allowed"] for r in rules
            ),
            "rules_not_approved_for_automatic_join": [
                r["instrument_id"] for r in rules if not r["size_identity_join_allowed"]
            ],
            "uni_7083_underlying_identity_supported": rules[1]["asset_identity_supported"],
            "rejected_uni_id": 4113,
            "iota_named_gap_asset_weeks_with_verified_alias": len(gaps)
            if rules[0]["size_identity_join_allowed"]
            else 0,
            "other_833_literal_leads_independently_approved": False,
            "canonical_joins_materialized": 0,
            "market_cap_rescaled": False,
            "price_histories_spliced": False,
            "historical_Size_publication_vintage_proven": False,
            "historical_eligible_universe_ready": False,
            "OOS_performance_inspected": False,
        }
        write_json(target / "summary.json", result)
        print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "summary"))
    args = parser.parse_args()
    if args.action == "summary":
        print(json.dumps(read_json(OUTPUT / "review_001/summary.json"), sort_keys=True))
        return
    log = ROOT / "reports/acquisition/early_size_identity_20261119.log"
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
