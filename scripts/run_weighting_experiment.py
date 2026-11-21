"""Experiment012: fixed-membership portfolio weighting, opened development only."""

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from audit_development_continuity import sha
from buffer_sensitivity_worker import PRODUCTS, context, write
from first_development_engine import HistoricalData, simulate
from portfolio_weighting_rules import (
    CAP,
    RANK_SHARES,
    SCHEMES,
    SIGMA_FLOOR,
    DailyRisk,
    build_schedule,
)
from prepare_validation_2023 import PREPARED, ROOT
from run_strategy_adjustments import BASE as PREVIOUS
from run_strategy_adjustments import export_case, full_model

BASE = ROOT / "data/interim/portfolio_weighting/v20261121_001"


def contract():
    return {"source_context": context(), "python": platform.python_version(), "platform": sys.platform,
            "schemes": list(SCHEMES), "daily_returns_window": 60, "sigma_floor_daily": SIGMA_FLOOR,
            "max_abs_weight": CAP, "rank_side_shares": RANK_SHARES.tolist(),
            "code_hashes": {name: sha(ROOT / name) for name in (
                "scripts/run_weighting_experiment.py", "scripts/portfolio_weighting_rules.py",
                "experiments/012_portfolio_weighting.md")}}


def bind(base, value):
    path = base / "run_contract.json"
    if path.exists() and json.loads(path.read_text()) != value:
        raise ValueError("Output bound to different code/input/runtime: choose a new --output version")
    if not path.exists():
        write(path, value)


def prepare(base):
    value = contract()
    bind(base, value)
    frame = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    if (frame.feature_cutoff_ms >= 1704067200000).any():
        raise ValueError("Unopened feature window encountered")
    hourly = pd.read_parquet(PREPARED / "trade.parquet", columns=["instrument_id", "bar_open_ms", "close"])
    risk = DailyRisk(hourly)
    daily = pd.concat([pd.DataFrame({"instrument_id": symbol, "available_ms": times, "close": prices})
                       for symbol, (times, prices) in risk.series.items()], ignore_index=True)
    folder = base / "prepared"
    folder.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(folder / "risk_closes.parquet", index=False)
    audit, plans, hashes = [], {}, {}
    for year in (2022, 2023):
        sample = full_model(frame, year)
        reference = json.loads((PREVIOUS / f"results/{year}/C_two_week/schedule.json").read_text())["weights"]
        for scheme in SCHEMES:
            weights, rows = build_schedule(sample, year, scheme, risk)
            if list(weights) != list(reference) or any(set(weights[d]) != set(reference[d]) for d in weights):
                raise ValueError("Weighting changed selected membership or decision dates")
            if scheme == "EQ" and weights != reference:
                raise ValueError("EQ differs from cached control weights")
            path = folder / f"{year}_{scheme}.json"
            write(path, {"weights": weights})
            hashes[path.name] = sha(path)
            plans[f"{year}/{scheme}"] = weights
            audit += rows
    pd.DataFrame(audit).to_csv(folder / "weight_audit.csv", index=False)
    hashes.update({name: sha(folder / name) for name in ("risk_closes.parquet", "weight_audit.csv")})
    write(folder / "summary.json", {"success": True, "schemes": list(SCHEMES), "years": [2022, 2023],
          "audit_rows": len(audit), "identical_selected_membership": True, "new_model_fits": 0,
          "risk_inputs_validated_before_PnL": True, "sealed_2024_and_final_OOS_inspected": False,
          "output_hashes": hashes})
    print(json.dumps({"success": True, "stage": "prepare", "audit_rows": len(audit), "risk_inputs_verified": True}), flush=True)
    return value, plans


def check_case(base, folder, year, scheme, bps, replay=False):
    marker = json.loads((folder / "_complete.json").read_text())
    if marker["key"] != [year, scheme, bps, replay] or marker["contract_sha256"] != sha(base / "run_contract.json"):
        raise ValueError("Case key/contract mismatch")
    if any(sha(folder / name) != digest for name, digest in marker["output_hashes"].items()):
        raise ValueError("Case output changed")
    plan = base / f"prepared/{year}_{scheme}.json"
    if sha(plan) != marker["schedule_sha256"]:
        raise ValueError("Case schedule changed")
    weights = json.loads(plan.read_text())["weights"]
    daily = pd.read_csv(folder / "daily.csv")
    fills, funding = [pd.read_csv(folder / f"{name}.csv") for name in ("fills", "funding")]
    if len(daily) != 365 or not (pd.to_datetime(daily.timestamp, utc=True).dt.year == year).all():
        raise ValueError("Daily grid/scope mismatch")
    if not np.isfinite(daily.strategy_nav).all() or (daily.strategy_nav <= 0).any() or not np.allclose(
            daily.strategy_nav, daily.cash_usdt+daily.unrealized_usdt, rtol=0, atol=.01):
        raise ValueError("NAV/cash/marked position mismatch")
    for column, total in (("commissions_usdt", fills.commission_usdt.sum()),
                          ("funding_cashflow_usdt", funding.cashflow_usdt.sum()),
                          ("traded_notional_usdt", fills.notional_usdt.sum())):
        if abs(daily[column].sum()-total) > .001:
            raise ValueError("Cash ledger mismatch")
    dates = pd.to_datetime(fills.timestamp_ns, unit="ns", utc=True)
    if not dates.dt.hour.isin([2, 23]).all() or not set(dates.dt.strftime("%Y-%m-%d")) <= set(weights) | {f"{year}-12-30"}:
        raise ValueError("Unscheduled fill")
    targets = pd.read_csv(folder / "targets.csv")
    for day, group in targets.groupby("decision_date"):
        actual = dict(zip(group[group.weight != 0].instrument_id, group[group.weight != 0].weight, strict=True))
        expected = weights.get(day, {})
        if set(actual) != set(expected) or any(abs(actual[k]-expected[k]) > 1e-12 for k in actual):
            raise ValueError("Actual weights differ from plan")
    engine = json.loads((folder / "engine_summary.json").read_text())
    if not engine["success"] or abs(engine["ledger_error_usdt"]) > .01:
        raise ValueError("Final engine reconciliation failed")
    if json.loads((folder / "diagnostic_metrics.json").read_text()) != marker["result"]:
        raise ValueError("Checkpoint metrics differ from verified output")
    if engine["financial_sha256"] != marker["result"]["financial_sha256"]:
        raise ValueError("Financial hash mismatch")
    if scheme == "EQ":
        ref = json.loads((PREVIOUS / f"results/{year}/C_two_week/slippage_{bps}bps/engine_summary.json").read_text())
        if engine != ref:
            raise ValueError("Cached EQ control changed")
    return marker["result"]


def execute_case(base, data, events, weights, year, scheme, bps, replay=False):
    folder = base / f"results/{year}/{scheme}" / ("primary_replay" if replay else f"slippage_{bps}bps")
    if (folder / "_complete.json").exists():
        return check_case(base, folder, year, scheme, bps, replay)
    attempt = folder / "attempts" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True, exist_ok=False)
    if scheme == "EQ":
        source = PREVIOUS / f"results/{year}/C_two_week/slippage_{bps}bps"
        for name in PRODUCTS:
            shutil.copyfile(source / name, attempt / name)
    else:
        simulate(data, events, weights, attempt, bps=bps)
    result = export_case(attempt, year)
    for name in PRODUCTS:
        shutil.copyfile(attempt / name, folder / name)
    write(folder / "_complete.json", {"key": [year, scheme, bps, replay],
          "contract_sha256": sha(base / "run_contract.json"), "schedule_sha256": sha(base / f"prepared/{year}_{scheme}.json"),
          "result": result, "output_hashes": {name: sha(folder / name) for name in PRODUCTS}})
    return check_case(base, folder, year, scheme, bps, replay)


def comparisons(table):
    rows = []
    primary = table[table.slippage_bps == 5].set_index(["year", "scheme"])
    for scheme in ("IV60", "RANK"):
        for year in (2022, 2023):
            row, eq = primary.loc[(year, scheme)], primary.loc[(year, "EQ")]
            stress = table[(table.year == year) & (table.scheme == scheme) & (table.slippage_bps == 10)].iloc[0]
            rows.append({"year": year, "scheme": scheme, "delta_return": row.total_return-eq.total_return,
                         "delta_sharpe": row.Sharpe_rf0-eq.Sharpe_rf0, "delta_MDD": row.MDD-eq.MDD,
                         "volatility_ratio": row.annualized_volatility/eq.annualized_volatility,
                         "notional_ratio": row.traded_notional/eq.traded_notional,
                         "primary_gate": bool(row.total_return > 0 and row.Sharpe_rf0 > eq.Sharpe_rf0
                             and row.MDD >= eq.MDD and row.other_months_compounded_return > 0),
                         "stress_positive": bool(stress.total_return > 0)})
    return pd.DataFrame(rows)


def verify(base):
    if contract() != json.loads((base / "run_contract.json").read_text()):
        raise ValueError("Code/source/runtime changed")
    prepared = json.loads((base / "prepared/summary.json").read_text())
    if any(sha(base / "prepared" / name) != digest for name, digest in prepared["output_hashes"].items()):
        raise ValueError("Prepared weight/risk audit changed")
    closes = pd.read_parquet(base / "prepared/risk_closes.parquet")
    risk = DailyRisk(closes.rename(columns={"available_ms": "bar_open_ms"}).assign(bar_open_ms=closes.available_ms-3_600_000))
    frame = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    rows = []
    for year in (2022, 2023):
        sample = full_model(frame, year)
        for scheme in SCHEMES:
            expected, _ = build_schedule(sample, year, scheme, risk)
            if expected != json.loads((base / f"prepared/{year}_{scheme}.json").read_text())["weights"]:
                raise ValueError("Weights do not reconstruct from past-only risk inputs")
            for bps in (5, 10):
                folder = base / f"results/{year}/{scheme}/slippage_{bps}bps"
                result = check_case(base, folder, year, scheme, bps)
                rows.append({"year": year, "scheme": scheme, "slippage_bps": bps, **result})
        replay = check_case(base, base / f"results/{year}/IV60/primary_replay", year, "IV60", 5, True)
        primary = check_case(base, base / f"results/{year}/IV60/slippage_5bps", year, "IV60", 5)
        if replay["financial_sha256"] != primary["financial_sha256"]:
            raise ValueError("IV60 financial replay mismatch")
    return pd.DataFrame(rows)


def run(base):
    value, plans = prepare(base)
    data = HistoricalData(PREPARED)
    rows = []
    for year in (2022, 2023):
        events = data.events(year, end_year=year)
        for scheme in SCHEMES:
            for bps in (5, 10):
                print(f"Run {year}/{scheme}/{bps}bps", flush=True)
                result = execute_case(base, data, events, plans[f"{year}/{scheme}"], year, scheme, bps)
                rows.append({"year": year, "scheme": scheme, "slippage_bps": bps, **result})
                pd.DataFrame(rows).to_csv(base / "progress.csv", index=False)
            if scheme == "IV60":
                execute_case(base, data, events, plans[f"{year}/{scheme}"], year, scheme, 5, True)
    if contract() != value:
        raise ValueError("Inputs changed during experiment")
    table = verify(base)
    table.to_csv(base / "all_runs.csv", index=False)
    paired = comparisons(table)
    paired.to_csv(base / "paired_comparisons.csv", index=False)
    supported = [scheme for scheme in ("IV60", "RANK") if paired[paired.scheme == scheme][["primary_gate", "stress_positive"]].to_numpy().all()]
    summary = {"success": True, "completed_cases": 12, "cached_controls": 4, "new_simulations": 8,
               "verified_replays": 2, "new_model_fits": 0, "supported_weighting_candidates": supported,
               "sealed_2024_and_final_OOS_inspected": False, "paper_or_live_ready": False}
    write(base / "summary.json", summary)
    print(json.dumps(summary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["prepare", "run", "report", "all", "summary"], default="all")
    parser.add_argument("--output", type=Path, default=BASE)
    args = parser.parse_args()
    if args.stage == "summary":
        print((args.output / "summary.json").read_text())
    elif args.stage == "prepare":
        prepare(args.output)
    else:
        if args.stage in ("run", "all"):
            run(args.output)
        if args.stage in ("report", "all"):
            subprocess.run([sys.executable, str(ROOT / "scripts/report_weighting_experiment.py"),
                            "--results", str(args.output)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
