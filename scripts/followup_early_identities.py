"""Fixed-source IOTA/UNI evidence supplement; no canonical data changes."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from html.parser import HTMLParser
from pathlib import Path

import verify_early_size_identities as prior
from acquire_usdm_universe import bind_run, digest, exclusive_run, read_json, write_json
from check_early_cases import normalized, verified_article
from collect_cmc_weekly import Downloader, LogTee, checked_source, raw_bytes

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/early_identity_followup_20261119.json"
OUTPUT = ROOT / "data/interim/early_identity_followup_20261119_v002"
REVIEW = OUTPUT / "review_002"
UNI_CODE = "300bf39679ee4110b440ee79185bc898"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors, self.href, self.label = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href, self.label = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self.href is not None:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.anchors.append((self.href, "".join(self.label)))
            self.href, self.label = None, []


def monthly_link(body):
    parser = Links()
    parser.feed(body.decode("utf-8"))
    return (
        "usdt-margined perpetual contracts" in prior.text(body)
        and any(
            url.rstrip("/").endswith("/" + UNI_CODE) and label.strip() == "UNI/USDT"
            for url, label in parser.anchors
        )
        and "uniswap" in prior.text(body)
    )


def article_check(body, code, fragments):
    payload = json.loads(body)
    article = payload.get("data") or {}
    if not payload.get("success") or article.get("code") != code:
        raise ValueError("official CMS article identity mismatch")
    content = article.get("body")
    if isinstance(content, str) and content.lstrip().startswith("<"):
        # Legacy CMS articles use HTML; newer articles use a serialized text tree.
        # Only the exact identified article body is searched, not related articles.
        content = prior.text(content.encode())
        missing = [part for part in fragments if normalized(part) not in normalized(content)]
        return (
            not missing,
            {
                "title": article["title"],
                "article_code": code,
                "clauses_verified": not missing,
                "missing_fragments": missing,
                "body_format": "legacy_html",
                "cms_publish_date_raw": article.get("publishDate"),
                "historical_content_version_proven": False,
                "causal_available_at": None,
            },
            content,
        )
    report, content = verified_article(body, code, fragments)
    return report["clauses_verified"], report, content


def supplemented_rules(previous, proof):
    rules = copy.deepcopy(previous)
    iota, uni = rules[:2]
    iota["size_identity_join_allowed"] = all(
        proof.get(key, False) for key in ("iota_historical_provider", "iota_units", "iota_origin")
    )
    uni["asset_identity_supported"] = all(
        proof.get(key, False)
        for key in ("uni_historical_provider_contract_origin", "uni_spot", "venue_month")
    )
    uni["futures_specific_2020_link_verified"] = bool(proof.get("uni_futures", False))
    uni["size_identity_join_allowed"] = (
        uni["asset_identity_supported"] and uni["futures_specific_2020_link_verified"]
    )
    uni["scope_from"] = "2020-09-18T07:00:00+00:00"
    uni["reason"] = (
        "combined official spot/project identity and futures launch evidence; no address in futures notice"
    )
    for row in rules[:2]:
        row["evidence_review"] = "early_identity_followup_20261119_v002"
        row["identity_evidence_is_retrospective"] = True
    return rules


def capture_once(config):
    path = OUTPUT / "capture_summary.json"
    if path.exists():
        report = read_json(path)
        if report["config_sha256"] != digest(CONFIG.read_bytes()):
            raise ValueError("capture contract changed")
        for attempt in (OUTPUT / "raw/attempts").rglob("*.json"):
            meta = read_json(attempt)
            body = attempt.with_suffix(".raw").read_bytes()
            if digest(body) != meta["sha256"] or len(body) != meta["bytes"]:
                raise ValueError("failed attempt integrity mismatch")
        return report, 0
    if (OUTPUT / "access_pause.json").exists():
        raise ValueError("capture stopped; no automatic retry")
    downloader = Downloader(OUTPUT, config["max_raw_bytes"])
    results, failures = [], []
    for spec in config["sources"]:
        try:
            _, meta, hit = downloader.get(spec["id"], spec["url"])
            results.append({"id": spec["id"], "source": meta, "cache_hit": hit})
        except Exception as exc:
            failures.append({"id": spec["id"], "error": str(exc)})
            if (OUTPUT / "access_pause.json").exists():
                break
    report = {
        "success": len(results) == len(config["sources"]),
        "config_sha256": digest(CONFIG.read_bytes()),
        "results": results,
        "failures": failures,
        "http_requests": downloader.requests,
        "raw_bytes": raw_bytes(OUTPUT),
    }
    write_json(path, report)
    return report, downloader.requests


def run():
    config = read_json(CONFIG)
    dependencies = (
        "verify_early_size_identities.py",
        "collect_cmc_weekly.py",
        "check_early_cases.py",
        "check_identity_followup.py",
        "review_contract_identity.py",
        "acquire_usdm_universe.py",
        "inventory_early_size.py",
    )
    contract = {
        "config_sha256": digest(CONFIG.read_bytes()),
        "script_sha256": digest(Path(__file__).read_bytes()),
        "dependencies": {
            name: digest((ROOT / "scripts" / name).read_bytes()) for name in dependencies
        },
    }
    with exclusive_run(OUTPUT / ".followup.lock"):
        source_contract = OUTPUT / "source_contract/run_config.json"
        if source_contract.exists() and (OUTPUT / "capture_summary.json").exists():
            original = read_json(source_contract)
            if (
                original["config_sha256"] != contract["config_sha256"]
                or original["dependencies"] != contract["dependencies"]
            ):
                raise ValueError("frozen capture configuration/dependencies changed")
            # Preserve the original capture tool binding; parser revisions must use
            # a separate review directory, never overwrite the previous review.
        else:
            bind_run(OUTPUT / "source_contract", contract)
        # Recompute and hash-check the frozen previous review using its own tool.
        prior.run()
        previous_root = prior.OUTPUT / "review_001"
        previous = read_json(previous_root / "mapping_decisions.json")
        old = read_json(previous_root / "proof_checks.json")
        capture, requests = capture_once(config)
        sources = {}
        for spec in config["sources"]:
            found = checked_source(OUTPUT, spec["id"], spec["url"])
            if found is not None:
                sources[spec["id"]] = found
        old_config = read_json(prior.CONFIG)
        spot_spec = next(s for s in old_config["sources"] if s["id"] == "uni_spot")
        spot_body = checked_source(prior.OUTPUT, "uni_spot", spot_spec["url"])[0]
        proof = {
            "iota_historical_provider": old["iota_history"] and old["iota_provider"],
            "uni_historical_provider_contract_origin": all(
                old[k] for k in ("uni_history", "uni_provider", "uni_contract", "uni_origin")
            ),
            "iota_units": False,
            "iota_origin": False,
            "uni_futures": False,
            "venue_month": False,
            "uni_spot": False,
        }
        clauses, issues = {}, []
        checks = (
            (
                "uni_spot",
                spot_body,
                "64d3dbe17d114c24b6c0007f48459f5f",
                ["Uniswap (UNI)", "UNI/USDT", "2020/09/17 3:00 AM (UTC)"],
            ),
            (
                "uni_futures",
                sources.get("uni_futures", (None,))[0],
                UNI_CODE,
                [
                    "UNI/USDT perpetual contract",
                    "2020/09/18 7:00 AM (UTC)",
                    "uses USDT as collateral",
                ],
            ),
            ("iota_units", sources.get("iota_units", (None,))[0], "115002193731", []),
        )
        for label, body, code, fragments in checks:
            if body is None:
                issues.append(label + ":missing captured source")
                continue
            try:
                passed, report, content = article_check(body, code, fragments)
                if label == "iota_units":
                    passed = passed and prior.iota_unit_clause(content.encode())
                if label == "uni_futures":
                    passed = passed and "UNI USDT-Margined Perpetual" in report["title"]
                proof[label], clauses[label] = passed, report
            except (ValueError, KeyError, TypeError) as exc:
                issues.append(label + ":" + str(exc))
        if "iota_origin" in sources:
            origin = prior.text(sources["iota_origin"][0])
            proof["iota_origin"] = all(
                fragment in origin
                for fragment in (
                    "new iota token denomination",
                    "what was previously 1 miota will now simply be one iota",
                )
            )
        if "venue_month" in sources:
            proof["venue_month"] = monthly_link(sources["venue_month"][0])
        rules = supplemented_rules(previous, proof)
        review = REVIEW
        binding = {
            **contract,
            "prior_artifact_hashes": {
                p.name: digest(p.read_bytes()) for p in previous_root.glob("*.json")
            },
            "source_hashes": {label: item[1]["sha256"] for label, item in sources.items()},
            "capture_summary_sha256": digest((OUTPUT / "capture_summary.json").read_bytes()),
            "capture_contract_sha256": digest(source_contract.read_bytes()),
        }
        bind_run(review, binding)
        write_json(review / "proof_checks.json", proof)
        write_json(review / "clauses.json", clauses)
        write_json(review / "mapping_decisions.json", rules)
        gaps = read_json(prior.INVENTORY / "full/asset_review_queue.json")
        iota_weeks = next(r for r in gaps if r["instrument_id"] == "IOTAUSDT")[
            "missing_size_in_price_history_weeks"
        ]
        summary = {
            "review_completed": True,
            "source_capture_complete": capture["success"],
            "source_http_requests_this_run": requests,
            "verified_sources": len(sources),
            "proof_checks_all_passed": all(proof.values()),
            "issues": issues,
            "verified_2020_identity_rules": sum(r["size_identity_join_allowed"] for r in rules),
            "new_identity_rules": [
                r["instrument_id"]
                for r, before in zip(rules, previous, strict=True)
                if r["size_identity_join_allowed"] and not before["size_identity_join_allowed"]
            ],
            "iota_named_gap_asset_weeks_with_verified_alias": len(iota_weeks)
            if rules[0]["size_identity_join_allowed"]
            else 0,
            "canonical_joins_materialized": 0,
            "other_literal_leads_independently_approved": False,
            "historical_Size_publication_vintage_proven": False,
            "historical_eligible_universe_ready": False,
            "OOS_performance_inspected": False,
        }
        write_json(review / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "summary"))
    args = parser.parse_args()
    if args.action == "summary":
        print(json.dumps(read_json(REVIEW / "summary.json"), sort_keys=True))
        return
    path = ROOT / "reports/acquisition/early_identity_followup_20261119_v002.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    print("Log: " + str(path), flush=True)
    with (
        path.open("a", encoding="utf-8") as handle,
        redirect_stdout(LogTee(sys.stdout, handle)),
        redirect_stderr(LogTee(sys.stderr, handle)),
    ):
        run()


if __name__ == "__main__":
    main()
