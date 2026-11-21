"""Audit warmup and weekly input coverage; never compute labels/model/PnL/OOS."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pyarrow.parquet as pq
from daily_input_rules import REASONS
from development_continuity_rules import (
    mapping_covers_window,
    mondays,
    normalized,
    numeric_history,
    seven_day_imbalance,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parents[1] / "data/canonical"
DEVELOPMENT = DATA / "binance_um_daily_research/v20261118_001"
EARLY = DATA / "binance_um_early_research/v20261119_001"
IDENTITY = ROOT / "data/interim/early_weekly_universe/v20261120_001/asset_review.json"
DEV_COLUMNS = [
    "instrument_id", "data_day", "reference_time_ms", "trade_close",
    "trade_close_valid_for_history", "partial_lifecycle_day", "known_lifecycle_order_block",
    "scoped_execution_block", "known_equity_episode", "episode_number", "close_episode_number",
    "imbalance_inputs_valid", "history120_consecutive_complete", "consecutive_daily_closes",
    "price_funding_data_candidate", "base_failure_mask", "trade_hours", "mark_hours",
]
EARLY_COLUMNS = [
    "instrument_id", "data_day", "reference_time_ms", "trade_close", "valid_closing_observation",
    "partial_confirmed_lifecycle_day", "audit_before_confirmed_launch",
    "audit_at_or_after_confirmed_settlement", "audit_span_crosses_confirmed_boundary",
    "audit_before_proposed_launch", "known_composite_index", "complete_trade_day",
    "trade_quote_volume_sum", "taker_buy_quote_volume_sum",
]
FIELDS = ["old_price_funding", "old_with_7day_imbalance", "hypothetical_bridge_with_7day_imbalance",
          "bridge_dependent_with_7day_imbalance", "existing_mapping_covers_lookback_and_splice"]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_verified(root, symbol, early=False):
    index_path, daily = root / "index" / f"{symbol}.json", root / "daily" / f"{symbol}.parquet"
    index = json.loads(index_path.read_text())
    if index["instrument_id"] != symbol or sha(daily) != index["daily_sha256"]:
        raise ValueError(f"Daily source integrity failure: {symbol}")
    start, end = ("2020-08-01", "2021-01-01") if early else ("2021-01-01", "2023-01-01")
    rows = pq.read_table(daily, columns=EARLY_COLUMNS if early else DEV_COLUMNS,
                         filters=[("data_day", ">=", start), ("data_day", "<", end)]).to_pylist()
    if any(r["instrument_id"] != symbol for r in rows):
        raise ValueError("Identifier mismatch")
    expected = 153 if early else 730
    if len(rows) != expected:
        raise ValueError(f"Expected {expected} daily observations for {symbol}, got {len(rows)}")
    return rows, {"index_sha256": sha(index_path), "daily_sha256": index["daily_sha256"],
                  "rows_loaded": len(rows), "loaded_window": [start, end]}


def run(output, full):
    started = time.monotonic()
    symbols = sorted(p.stem for p in (DEVELOPMENT / "daily").glob("*.parquet"))
    if len(symbols) != 924:
        raise ValueError("Full source inventory must contain 924 identifiers")
    if not full:
        symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LENDUSDT", "DEFIUSDT"]
    identities = {r["instrument_id"]: r for r in json.loads(IDENTITY.read_text())}
    calendar = mondays()
    coverage = {d: {k: 0 for k in FIELDS} for d in calendar}
    assets, august, bindings = [], [], {}
    august_day = date(2022, 7, 31)
    for symbol in symbols:
        development, binding = read_verified(DEVELOPMENT, symbol)
        early, early_binding = [], None
        if (EARLY / "daily" / f"{symbol}.parquet").exists():
            early, early_binding = read_verified(EARLY, symbol, early=True)
        bindings[symbol] = {"development": binding, "early": early_binding}
        points = [normalized(r, early=True) for r in early] + [normalized(r) for r in development]
        history = numeric_history(points)
        by_day = {r["day"]: r for r in points}
        legacy = {date.fromisoformat(r["data_day"]): r for r in development}
        identity = identities.get(symbol, {})
        mapping = identity.get("mapping_record") or {}
        mapping = mapping.get("mapping") or {}
        dependent_dates = []
        for decision in calendar:
            day = decision - timedelta(days=1)
            row = legacy[day]
            imbalance = seven_day_imbalance(day, by_day)
            candidate = history[day] >= 121 and (row["base_failure_mask"] & ~8) == 0 and imbalance
            bridge_dependent = (candidate and day - timedelta(days=120) < date(2021, 1, 1)
                                and not row["history120_consecutive_complete"])
            flags = [bool(row["price_funding_data_candidate"]),
                     bool(row["price_funding_data_candidate"] and imbalance), bool(candidate),
                     bool(bridge_dependent), mapping_covers_window(mapping, day)]
            for key, flag in zip(FIELDS, flags, strict=True):
                coverage[decision][key] += int(flag)
            if bridge_dependent:
                dependent_dates.append(decision.isoformat())
        old_first = next((r["data_day"] for r in development
                          if r["history120_consecutive_complete"]), None)
        numeric_first = next((r["data_day"] for r in development
                              if history[date.fromisoformat(r["data_day"])] >= 121), None)
        assets.append({
            "instrument_id": symbol, "early_file_exists": bool(early),
            "early_tail_valid_closes": history.get(date(2020, 12, 31), 0),
            "jan03_hypothetical_valid_closes": history[date(2021, 1, 3)],
            "old_first_120day_history": old_first, "hypothetical_first_120day_history": numeric_first,
            "bridge_dependent_decisions": dependent_dates,
            "early_identity_status": identity.get("identity_status", "not_in_early_review"),
            "mapping_scope_from": mapping.get("scope_from"),
            "mapping_scope_to_exclusive": mapping.get("scope_to_exclusive"),
            "historical_strategy_eligible": False,
        })
        row = legacy[august_day]
        invalid = [r["day"].isoformat() for r in points
                   if august_day - timedelta(days=120) <= r["day"] <= august_day and not r["valid"]]
        august.append({
            "instrument_id": symbol, "feature_day": august_day.isoformat(),
            "old_price_funding_candidate": row["price_funding_data_candidate"],
            "old_failure_mask": row["base_failure_mask"],
            "old_failure_reasons": [k for k, value in REASONS.items()
                                    if row["base_failure_mask"] & value],
            "trade_hours": row["trade_hours"], "mark_hours": row["mark_hours"],
            "old_valid_close_streak": row["consecutive_daily_closes"],
            "recomputed_valid_close_streak": history[august_day],
            "invalid_close_dates_last121": invalid,
            "seven_day_imbalance_valid": seven_day_imbalance(august_day, by_day),
        })
    rows = [{"decision_date": d.isoformat(), **coverage[d]} for d in calendar]
    products = {"asset_audit.json": assets, "weekly_coverage.json": rows,
                "august_2022_reasons.json": august, "source_bindings.json": bindings}
    contract = {
        "schema": 1, "scope": "full" if full else "pilot", "identifiers": symbols,
        "script_sha256": sha(Path(__file__)),
        "rules_sha256": sha(ROOT / "scripts/development_continuity_rules.py"),
        "legacy_rules_sha256": sha(ROOT / "scripts/daily_input_rules.py"),
        "registration_sha256": sha(ROOT / "experiments/003_development_continuity_audit.md"),
        "identity_sha256": sha(IDENTITY), "source_bindings": bindings,
    }
    output.mkdir(parents=True, exist_ok=True)
    contract_path = output / "run_contract.json"
    if contract_path.exists() and json.loads(contract_path.read_text()) != contract:
        raise ValueError("Run inputs/code changed: choose a new output directory")
    write(contract_path, contract)
    old_hashes = {name: sha(output / name) for name in products if (output / name).exists()}
    for name, product in products.items():
        write(output / name, product)
    hashes = {name: sha(output / name) for name in products}
    if old_hashes and old_hashes != hashes:
        raise ValueError("Replay is not deterministic")
    stats = {key: {"minimum": min(r[key] for r in rows),
                   "median": statistics.median(r[key] for r in rows),
                   "maximum": max(r[key] for r in rows)} for key in FIELDS}
    summary = {
        "success": True, "full_scope": full, "identifiers": len(symbols),
        "early_files_loaded": sum(a["early_file_exists"] for a in assets), "weekly_decisions": 104,
        "weekly_counts": stats, "first_week": rows[0],
        "bridge_dependent_identifiers": sum(bool(a["bridge_dependent_decisions"]) for a in assets),
        "bridge_dependent_asset_weeks": sum(len(a["bridge_dependent_decisions"]) for a in assets),
        "august_2022_legacy_reason_counts": dict(Counter(
            reason for row in august for reason in row["old_failure_reasons"])),
        "replay_hashes_identical": bool(old_hashes), "output_hashes": hashes,
        "historical_eligible_universe_ready": False, "real_market_backtest_ready": False,
        "funding_check": "latest observed rate freshness only, not 7day sum or paid cashflow",
        "hypothetical_bridge_is_identity_approval": False,
        "OOS_performance_inspected": False, "PnL_computed": False, "labels_computed": False,
        "model_fitted": False, "source_http_requests": 0,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    write(output / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or ROOT / "data/interim/development_continuity/v20261121_001" / (
        "full" if args.full else "pilot")
    run(output, args.full)


if __name__ == "__main__":
    main()
