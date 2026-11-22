"""Bounded public evidence snapshots and all-identifier product-scope accounting."""

import json
from pathlib import Path

import pandas as pd

from .config import load_json, sha
from .repair import RateGate, request, write_json

PHASE_CODES = {
    "PUMPUSDT": "e220b78bdf4848e3a61eb9fce99e2580",
    "LITUSDT": "96ac152ced224d7a92a10a11335f5212",
}


def collect_evidence(folder):
    folder = Path(folder)
    jobs = [
        (
            symbol,
            "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode="
            + code,
            code,
        )
        for symbol, code in PHASE_CODES.items()
    ]
    jobs.append(("exchange_info", "https://fapi.binance.com/fapi/v1/exchangeInfo", None))
    results = {}
    gate = RateGate()
    for key, url, code in jobs:
        directory = folder / "evidence" / key
        path = directory / "source.json"
        try:
            if path.exists():
                source = load_json(path)
                if source["url"] != url or sha(source["path"]) != source["sha256"]:
                    raise ValueError("Evidence snapshot identity changed")
                payload = load_json(source["path"])
            else:
                body, source = request(url, directory, gate)
                payload = json.loads(body)
                if code:
                    source["article_code"] = code
                write_json(path, source)
            if code and (
                not payload.get("success")
                or payload["data"]["code"] != code
                or "Standard Perpetual" not in payload["data"]["title"]
            ):
                raise ValueError("Official transition article validation failed")
            if not code and not isinstance(payload.get("symbols"), list):
                raise ValueError("Exchange information schema mismatch")
            results[key] = {"verified": True, "source_sha256": source["sha256"], "url": url}
        except Exception as exc:
            results[key] = {"verified": False, "error": str(exc)}
    write_json(folder / "evidence_status.json", results)
    print(json.dumps(results), flush=True)
    return results


def scope_report(root, folder):
    root, folder = Path(root), Path(folder)
    plan = load_json(folder / "plan.json")
    dataset = Path(plan["dataset"])
    manifest = load_json(dataset / "manifest.json")
    assets_path = dataset / "asset_summary.csv"
    if sha(assets_path) != manifest["output_hashes"]["asset_summary.csv"]:
        raise ValueError("Asset accounting table changed")
    source = load_json(folder / "evidence/exchange_info/source.json")
    if sha(source["path"]) != source["sha256"]:
        raise ValueError("Exchange information snapshot changed")
    metadata = {item["symbol"]: item for item in load_json(source["path"])["symbols"]}
    assets = pd.read_csv(assets_path)
    rows = []
    for asset in assets.to_dict("records"):
        item = metadata.get(asset["instrument_id"], {})
        underlying = item.get("underlyingType", "NOT_IN_CURRENT_RESPONSE")
        noncrypto = underlying not in {"COIN", "PREMARKET", "NOT_IN_CURRENT_RESPONSE"}
        rows.append(
            {
                "instrument_id": asset["instrument_id"],
                "ever_provisional_candidate": asset["candidate_decisions"] > 0,
                "current_underlying_type": underlying,
                "current_contract_type": item.get("contractType"),
                "current_onboard_ms": item.get("onboardDate"),
                "current_status": item.get("status"),
                "dated_scope_disposition": "noncrypto_current_episode_requires_dated_scope"
                if noncrypto
                else "current_coin_metadata_not_full_historical_identity_proof"
                if underlying == "COIN"
                else "current_premarket_requires_phase_evidence"
                if underlying == "PREMARKET"
                else "not_in_current_response_keep_historical_review",
                "source_sha256": source["sha256"],
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(folder / "current_product_scope.csv", index=False)
    summary = {
        "identifiers_accounted": len(frame),
        "current_metadata_matches": int(
            frame.current_underlying_type.ne("NOT_IN_CURRENT_RESPONSE").sum()
        ),
        "types": frame.current_underlying_type.value_counts().to_dict(),
        "types_among_ever_provisional": frame[frame.ever_provisional_candidate]
        .current_underlying_type.value_counts()
        .to_dict(),
        "current_snapshot_is_not_historical_pit_proof": True,
        "whole_identifier_exclusions_applied": False,
        "source": source,
        "output_sha256": sha(folder / "current_product_scope.csv"),
    }
    write_json(folder / "product_scope_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "source"}), flush=True)
    return summary
