"""Experiment011 worker: prepare, synthetic pilot, resumable user-run simulations."""

import argparse
import json
import shutil
from datetime import UTC, datetime
from importlib.metadata import version
from types import SimpleNamespace

import numpy as np
import pandas as pd
from audit_development_continuity import sha
from first_development_engine import HistoricalData, simulate
from prepare_validation_2023 import PREPARED, ROOT
from run_strategy_adjustments import BASE as PREVIOUS
from run_strategy_adjustments import export_case, fold_sources, full_model
from two_week_buffer_rules import RETENTION_RANKS, schedule

BASE = ROOT / "data/interim/buffer_sensitivity/v20261121_001"
RESULTS = BASE / "results"
CORE_PACKAGES = ("nautilus_trader", "lightgbm", "shap", "pandas", "numpy")
PRODUCTS = ("engine_daily.csv", "daily.csv", "fills.csv", "funding.csv", "targets.csv",
            "engine_summary.json", "metrics.csv", "monthly_returns.csv", "diagnostic_metrics.json")


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def context():
    previous = json.loads((PREVIOUS / "results/summary.json").read_text())
    prior_contract = json.loads((PREVIOUS / "results/run_contract.json").read_text())
    runtime = {name: version(name) for name in CORE_PACKAGES}
    if not previous["success"] or previous["registered_cases"] != 32:
        raise ValueError("Complete verified Experiment010 cache required")
    if sha(ROOT / "scripts/first_development_engine.py") != prior_contract["engine_sha256"]:
        raise ValueError("Execution engine differs from cached010 controls")
    if runtime != prior_contract["runtime"]:
        raise ValueError(f"Core package versions differ from verified010 runtime: expected={prior_contract['runtime']}, got={runtime}. Use --python with the existing Windows runtime; no packages changed.")
    meta = json.loads((PREPARED / "manifest.json").read_text())
    if any(sha(PREPARED / name) != digest for name, digest in meta["output_hashes"].items()):
        raise ValueError("Prepared source hash mismatch")
    files = [PREPARED / "manifest.json", PREVIOUS / "results/summary.json", PREVIOUS / "results/all_runs.csv"]
    for year in (2022, 2023):
        source, spot = fold_sources(year)
        files += [source / "model" / name for name in ("lightgbm.txt", "training_samples.parquet", "validation_predictions.parquet", "shap_values.csv")]
        files += [spot / f"{symbol}_{year}.csv" for symbol in ("BTCUSDT", "ETHUSDT")]
        files.append(PREVIOUS / f"results/{year}/C_two_week/schedule.json")
        for bps in (5, 10):
            files += [PREVIOUS / f"results/{year}/C_two_week/slippage_{bps}bps" / name for name in PRODUCTS]
    code = ["scripts/buffer_sensitivity_worker.py", "scripts/two_week_buffer_rules.py",
            "scripts/first_development_engine.py", "scripts/run_strategy_adjustments.py",
            "scripts/strategy_adjustment_rules.py", "scripts/run_first_development.py",
            "src/momentum_data/backtest_analysis.py", "experiments/011_two_week_buffer_sensitivity.md"]
    contract = {"runtime": runtime, "entry_rank": 5, "retention_ranks": list(RETENTION_RANKS),
                "rebalance_weeks": 2, "years": [2022, 2023], "slippage_bps": [5, 10],
                "source_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in files},
                "code_hashes": {name: sha(ROOT / name) for name in code}}
    return contract


def bind_contract(contract):
    path = RESULTS / "run_contract.json"
    if path.exists() and json.loads(path.read_text()) != contract:
        raise ValueError("Experiment version bound to changed code/input/runtime; preserve it and register a new version")
    if not path.exists():
        write(path, contract)


def prepare():
    contract = context()
    bind_contract(contract)
    frame = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    if (frame.feature_cutoff_ms >= 1704067200000).any():
        raise ValueError("Sealed-period features encountered")
    rows, schedule_hashes = [], {}
    for year in (2022, 2023):
        sample = full_model(frame, year)
        for rank in RETENTION_RANKS:
            weights, audit = schedule(sample, year, rank)
            if rank == 5:
                old = json.loads((PREVIOUS / f"results/{year}/C_two_week/schedule.json").read_text())["weights"]
                if weights != old:
                    raise ValueError("No-buffer control differs from verified010 two-week baseline")
            path = BASE / f"preparation/{year}/retain_{rank:02d}.json"
            write(path, {"weights": weights, "audit": audit})
            schedule_hashes[path.relative_to(BASE).as_posix()] = sha(path)
            rows.append({"year": year, "retention_rank": rank, "buffer_width": rank-5,
                         "rebalance_decisions": len(weights), "validation_rows": len(sample),
                         "membership_entries": sum(r["membership_entries"] for r in audit),
                         "membership_exits": sum(r["membership_exits"] for r in audit)})
    write(BASE / "preparation/summary.json", {"success": True, "prepared_settings": rows, "schedule_hashes": schedule_hashes,
          "expected_historical_cases": 16, "new_historical_cases": 12, "historical_runs_executed": False,
          "new_model_fits": 0, "sealed_2024_and_final_OOS_inspected": False,
          "note": "Preparation only; no candidate historical PnL computed. Initial10entries included in membership counts; final forced exits excluded."})
    print(json.dumps({"success": True, "stage": "prepare", "settings": len(rows), "historical_runs_executed": False}), flush=True)
    return contract


def checkpoint(folder, result, case):
    plan = BASE / f"preparation/{case['year']}/retain_{case['retention_rank']:02d}.json"
    write(folder / "case_manifest.json", {**case, "contract_sha256": sha(RESULTS / "run_contract.json"),
          "schedule_sha256": sha(plan)})
    hashes = {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != "_complete.json"}
    write(folder / "_complete.json", {"success": True, "case": case, "result": result, "output_hashes": hashes})


def read_checkpoint(folder):
    path = folder / "_complete.json"
    if not path.exists():
        return None
    marker = json.loads(path.read_text())
    if not marker["success"] or any(sha(folder / name) != digest for name, digest in marker["output_hashes"].items()):
        raise ValueError(f"Checkpoint corruption; refusing reuse: {folder}")
    manifest = json.loads((folder / "case_manifest.json").read_text())
    if manifest["contract_sha256"] != sha(RESULTS / "run_contract.json"):
        raise ValueError("Checkpoint belongs to different run contract")
    plan = BASE / f"preparation/{marker['case']['year']}/retain_{marker['case']['retention_rank']:02d}.json"
    if sha(plan) != manifest["schedule_sha256"]:
        raise ValueError("Checkpoint schedule changed")
    return marker


def verify_case(folder, year, weights):
    marker = read_checkpoint(folder)
    if marker is None:
        raise ValueError(f"Incomplete case: {folder}")
    daily = pd.read_csv(folder / "daily.csv")
    if len(daily) != 365 or not (pd.to_datetime(daily.timestamp, utc=True).dt.year == year).all():
        raise ValueError("NAV scope/grid mismatch")
    if not np.isfinite(daily.strategy_nav).all() or (daily.strategy_nav <= 0).any() or not np.allclose(
            daily.strategy_nav, daily.cash_usdt+daily.unrealized_usdt, rtol=0, atol=.01):
        raise ValueError("NAV identity failed")
    fills, funding = [pd.read_csv(folder / f"{name}.csv") for name in ("fills", "funding")]
    for col, amount in (("commissions_usdt", fills.commission_usdt.sum()),
                        ("funding_cashflow_usdt", funding.cashflow_usdt.sum()),
                        ("traded_notional_usdt", fills.notional_usdt.sum())):
        if abs(daily[col].sum()-amount) > .001:
            raise ValueError("Daily ledger mismatch")
    times = pd.to_datetime(fills.timestamp_ns, unit="ns", utc=True)
    if not times.dt.hour.isin([2, 23]).all() or not set(times.dt.strftime("%Y-%m-%d")) <= set(weights) | {f"{year}-12-30"}:
        raise ValueError("Unscheduled trade")
    targets = pd.read_csv(folder / "targets.csv")
    for day, group in targets.groupby("decision_date"):
        actual = dict(zip(group[group.weight != 0].instrument_id, group[group.weight != 0].weight, strict=True))
        if actual != weights.get(day):
            raise ValueError("Actual weights differ from scheduled membership")
    engine = json.loads((folder / "engine_summary.json").read_text())
    if not engine["success"] or abs(engine["ledger_error_usdt"]) > .01 or abs(engine["ending_nav"]-daily.strategy_nav.iloc[-1]) > .01:
        raise ValueError("Final account/engine reconciliation failed")
    return marker


def execute_case(year, rank, bps, weights, data, events, replay=False):
    root = RESULTS / str(year) / f"retain_{rank:02d}"
    folder = root / ("primary_replay" if replay else f"slippage_{bps}bps")
    case = {"year": year, "retention_rank": rank, "slippage_bps": bps, "replay": replay}
    old = read_checkpoint(folder)
    if old:
        if old["case"] != case:
            raise ValueError("Checkpoint case identity mismatch")
        print(f"Verified cached {case}", flush=True)
        return verify_case(folder, year, weights)
    attempt = folder / "attempts" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True, exist_ok=False)
    if rank == 5:
        source = PREVIOUS / f"results/{year}/C_two_week/slippage_{bps}bps"
        for name in PRODUCTS:
            shutil.copyfile(source / name, attempt / name)
    else:
        simulate(data, events, weights, attempt, bps=bps)
    result = export_case(attempt, year)
    if rank == 5:
        expected = json.loads((PREVIOUS / f"results/{year}/C_two_week/slippage_{bps}bps/engine_summary.json").read_text())
        if result["financial_sha256"] != expected["financial_sha256"]:
            raise ValueError("Cached no-buffer financial identity differs")
    for name in PRODUCTS:
        shutil.copyfile(attempt / name, folder / name)
    checkpoint(folder, result, case)
    return verify_case(folder, year, weights)


def comparison_table(table):
    primary = table[table.slippage_bps == 5].set_index(["year", "retention_rank"])
    rows = []
    for rank in RETENTION_RANKS[1:]:
        for year in (2022, 2023):
            row, base = primary.loc[(year, rank)], primary.loc[(year, 5)]
            stress = table[(table.year == year) & (table.retention_rank == rank) & (table.slippage_bps == 10)].iloc[0]
            primary_pass = bool(row.total_return > 0 and row.Sharpe_rf0 > base.Sharpe_rf0 and row.MDD >= base.MDD
                                and row.traded_notional < base.traded_notional and row.other_months_compounded_return > 0)
            rows.append({"year": year, "retention_rank": rank, "delta_return": row.total_return-base.total_return,
                         "delta_sharpe": row.Sharpe_rf0-base.Sharpe_rf0, "delta_MDD": row.MDD-base.MDD,
                         "notional_ratio": row.traded_notional/base.traded_notional, "primary_gate": primary_pass,
                         "stress_positive": bool(stress.total_return > 0)})
    return pd.DataFrame(rows)


def verify_results():
    contract = context()
    if json.loads((RESULTS / "run_contract.json").read_text()) != contract:
        raise ValueError("Results contract no longer matches code/input/runtime")
    rows = []
    preparation = json.loads((BASE / "preparation/summary.json").read_text())
    if any(sha(BASE / name) != digest for name, digest in preparation["schedule_hashes"].items()):
        raise ValueError("Prepared schedules changed")
    for year in (2022, 2023):
        for rank in RETENTION_RANKS:
            weights = json.loads((BASE / f"preparation/{year}/retain_{rank:02d}.json").read_text())["weights"]
            counts = next(r for r in preparation["prepared_settings"] if r["year"] == year and r["retention_rank"] == rank)
            for bps in (5, 10):
                folder = RESULTS / str(year) / f"retain_{rank:02d}/slippage_{bps}bps"
                marker = verify_case(folder, year, weights)
                if marker["case"] != {"year": year, "retention_rank": rank, "slippage_bps": bps, "replay": False}:
                    raise ValueError("Case key mismatch")
                if rank == 5:
                    control = json.loads((PREVIOUS / f"results/{year}/C_two_week/slippage_{bps}bps/engine_summary.json").read_text())
                    if marker["result"]["financial_sha256"] != control["financial_sha256"]:
                        raise ValueError("No-buffer identity mismatch")
                rows.append({"year": year, "retention_rank": rank, "buffer_width": rank-5, "slippage_bps": bps,
                             "membership_entries": counts["membership_entries"], "membership_exits": counts["membership_exits"],
                             **marker["result"]})
        weights = json.loads((BASE / f"preparation/{year}/retain_08.json").read_text())["weights"]
        replay = verify_case(RESULTS / str(year) / "retain_08/primary_replay", year, weights)
        original = read_checkpoint(RESULTS / str(year) / "retain_08/slippage_5bps")
        if replay["result"]["financial_sha256"] != original["result"]["financial_sha256"]:
            raise ValueError("Rank8 financial replay mismatch")
    return pd.DataFrame(rows)


def run():
    contract = prepare()
    frame = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    data = HistoricalData(PREPARED)
    rows = []
    for year in (2022, 2023):
        events = data.events(year, end_year=year)
        sample = full_model(frame, year)
        for rank in RETENTION_RANKS:
            weights, _ = schedule(sample, year, rank)
            for bps in (5, 10):
                print(f"Case {year} retain={rank} slippage={bps}bps", flush=True)
                marker = execute_case(year, rank, bps, weights, data, events)
                rows.append({"year": year, "retention_rank": rank, "slippage_bps": bps, **marker["result"]})
                pd.DataFrame(rows).to_csv(RESULTS / "progress.csv", index=False)
            if rank == 8:
                replay = execute_case(year, rank, 5, weights, data, events, replay=True)
                primary = read_checkpoint(RESULTS / str(year) / "retain_08/slippage_5bps")
                if replay["result"]["financial_sha256"] != primary["result"]["financial_sha256"]:
                    raise ValueError("Replay differs from primary case")
    if context() != contract:
        raise ValueError("Inputs changed during experiment")
    table = verify_results()
    table.to_csv(RESULTS / "all_runs.csv", index=False)
    pairs = comparison_table(table)
    pairs.to_csv(RESULTS / "paired_comparisons.csv", index=False)
    supported = [rank for rank in RETENTION_RANKS[1:] if
                 pairs[pairs.retention_rank == rank][["primary_gate", "stress_positive"]].to_numpy().all()]
    grid = list(RETENTION_RANKS[1:])
    neighbors = {str(rank): [r for r in supported if abs(grid.index(r)-grid.index(rank)) == 1] for rank in supported}
    report = {"success": True, "completed_cases": len(table), "expected_cases": 16, "cached_controls": 4,
              "new_historical_simulations": 12, "verified_replays": 2, "new_model_fits": 0,
              "supported_retention_ranks": supported, "passing_neighbors": neighbors,
              "primary_results": table[table.slippage_bps == 5][["year", "retention_rank", "total_return",
                  "Sharpe_rf0", "MDD", "traded_notional", "other_months_compounded_return"]].to_dict("records"),
              "sealed_2024_and_final_OOS_inspected": False, "paper_or_live_ready": False,
              "interpretation": "Development sensitivity study; no automatic threshold selection or new-window execution."}
    write(RESULTS / "summary.json", report)
    print(json.dumps(report), flush=True)


def pilot(destination=None):
    """Small synthetic20-asset/16-day accounting test, not historical strategy PnL."""
    destination = destination or BASE / "pilot" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    names = "AAVE ADA ALGO ATOM BAT BNB BTC COMP DASH DOGE DOT EOS ETC ETH IOST IOTA KAVA LINK LTC MKR".split()
    names = [name+"USDT" for name in names]
    start = int(pd.Timestamp("2022-01-03", tz="UTC").timestamp()*1000)
    hour, day_ms = 3_600_000, 86_400_000
    changed = names[1:6]+names[:1]+names[6:]
    frame = pd.concat([pd.DataFrame({"decision_date": text, "instrument_id": order, "score": range(20, 0, -1)})
                       for text, order in (("2022-01-03", names), ("2022-01-17", changed))])
    weights, _ = schedule(frame, 2022, 8)
    data = SimpleNamespace(symbols=names, trades={s: {start+i*day_ms: (100., 10., 1000.) for i in (0, 7, 14)} for s in names})
    events = []

    def add(symbol, stamp, kind, mark=False, offset=0, rate=None):
        events.append({"symbol": symbol, "stamp": stamp*1_000_000+offset, "kind": kind,
                       "price": 100., "mark_at": stamp if mark else None, "rate": rate})

    for i in range(17):
        now = start+i*day_ms
        for symbol in names:
            add(symbol, now, "mark", mark=True)
        add("BTCUSDT", now, "snapshot", offset=100)
        if i in (0, 7, 14):
            for symbol in names:
                add(symbol, now+hour, "reference", mark=True)
                add(symbol, now+2*hour, "execution")
            add("BTCUSDT", now+hour, "decision", offset=100)
            add("BTCUSDT", now+2*hour, "check", offset=100)
    add(names[0], start+day_ms+8*hour, "funding", mark=True, rate=.001)
    add(names[-1], start+day_ms+8*hour, "funding", mark=True, rate=.002)
    final = start+15*day_ms+23*hour
    for symbol in names:
        add(symbol, final, "final")
    add("BTCUSDT", final, "final_check", offset=100)
    _, result = simulate(data, sorted(events, key=lambda r: (r["stamp"], r["symbol"])), weights, destination, bps=0)
    funding = pd.read_csv(destination / "funding.csv")
    targets = pd.read_csv(destination / "targets.csv")
    if set(targets.decision_date) != {"2022-01-03", "2022-01-17"}:
        raise ValueError("Synthetic skipped week was resized")
    if set(targets[targets.decision_date == "2022-01-17"].instrument_id) != set(names[:5]+names[-5:]):
        raise ValueError("Synthetic rank6 holding was not retained")
    if abs(funding.cashflow_usdt.sum()-10.) > .001 or abs(result["ending_nav"]-99910.) > .01:
        raise ValueError("Synthetic funding/fee ledger mismatch")
    report = {"success": True, "synthetic_only": True, "historical_runs_executed": False,
              "funding_cashflow_usdt": float(funding.cashflow_usdt.sum()), "expected_final_cash": 99910.,
              "actual_final_cash": result["ending_nav"], "days": 16, "instruments": 20}
    write(destination / "pilot_summary.json", report)
    write(BASE / "pilot_summary.json", report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["prepare", "pilot", "run"], required=True)
    mode = parser.parse_args().mode
    {"prepare": prepare, "pilot": pilot, "run": run}[mode]()
