"""Experiment010: bounded execution changes and feature diagnostics,2022/2023only."""

import argparse
import json
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

import lightgbm as lgb
import matplotlib
import numpy as np
import pandas as pd
import shap
from audit_development_continuity import sha
from first_development_engine import HistoricalData, simulate
from prepare_validation_2023 import FEATURES, PREPARED, ROOT, write
from run_first_development import PARAMS
from strategy_adjustment_rules import CONFIGS, portfolio_schedule, training_rows

matplotlib.use("Agg")

sys.path.insert(0, str(ROOT / "src"))
from momentum_data.backtest_analysis import performance_tables, validate_daily  # noqa: E402

BASE = ROOT / "data/interim/strategy_adjustments/v20261121_001"
FIRST = ROOT / "data/interim/first_development/v20261121_001"
NEXT = ROOT / "data/interim/validation_2023/v20261121_001"


def fold_sources(year):
    base = FIRST if year == 2022 else NEXT
    results = base / ("results_v003" if year == 2022 else "results")
    return results, base / "spot_benchmarks"


def full_model(frame, year):
    results, _ = fold_sources(year)
    folder = results / "model"
    cut = int(pd.Timestamp(f"{year}-01-01", tz="UTC").timestamp()*1000)
    train = training_rows(frame, cut)
    saved = pd.read_parquet(folder / "training_samples.parquet").reset_index(drop=True)
    pd.testing.assert_frame_equal(train, saved, check_exact=True, check_dtype=False)
    sample = pd.read_parquet(folder / "validation_predictions.parquet").reset_index(drop=True)
    expected = frame[frame.decision_date.str[:4] == str(year)].reset_index(drop=True)
    pd.testing.assert_frame_equal(sample[expected.columns], expected, check_exact=True, check_dtype=False)
    booster = lgb.Booster(model_file=str(folder / "lightgbm.txt"))
    if not np.allclose(booster.predict(sample[FEATURES]), sample.score, rtol=0, atol=1e-12):
        raise ValueError("Full-model cache prediction mismatch")
    return sample


def ablated_model(frame, year, config, directory):
    cut = int(pd.Timestamp(f"{year}-01-01", tz="UTC").timestamp()*1000)
    train = training_rows(frame, cut)
    sample = frame[frame.decision_date.str[:4] == str(year)].reset_index(drop=True).copy()
    columns = [name for name in FEATURES if name not in CONFIGS[config]["drop"]]
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "metadata.json").exists():
        meta = json.loads((directory / "metadata.json").read_text())
        pd.testing.assert_frame_equal(train, pd.read_parquet(directory / "training_samples.parquet"))
        if meta["parameters"] != PARAMS or meta["features"] != columns or sha(directory / "lightgbm.txt") != meta["model_sha256"]:
            raise ValueError("Ablation cache mismatch")
        booster = lgb.Booster(model_file=str(directory / "lightgbm.txt"))
    else:
        model = lgb.LGBMRegressor(**PARAMS)
        model.fit(train[columns], train.label)
        booster = model.booster_
        booster.save_model(str(directory / "lightgbm.txt"))
    sample["score"] = booster.predict(sample[columns])
    explainer = shap.TreeExplainer(booster, feature_perturbation="tree_path_dependent")
    values = np.asarray(explainer.shap_values(sample[columns], check_additivity=True))
    expected = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    error = float(np.max(np.abs(values.sum(axis=1)+expected-sample.score.to_numpy())))
    if not np.isfinite(values).all() or error > 1e-6:
        raise ValueError("Ablation SHAP verification failed")
    attributed = sample[["instrument_id", "decision_date", "score"]].copy()
    for index, name in enumerate(columns):
        attributed[f"shap_{name}"] = values[:, index]
    attributed["expected_value"] = expected
    attributed.to_csv(directory / "shap_values.csv", index=False)
    pd.Series(np.abs(values).mean(axis=0), index=columns, name="mean_absolute_SHAP").to_csv(directory / "shap_importance.csv")
    train.to_parquet(directory / "training_samples.parquet", index=False)
    sample.to_parquet(directory / "validation_predictions.parquet", index=False)
    write(directory / "metadata.json", {"fit_count": 1, "year": year, "features": columns,
          "parameters": PARAMS, "train_rows": len(train), "validation_rows": len(sample),
          "latest_label_available_ms": int(train.label_available_ms.max()), "cutoff_ms": cut,
          "shap_max_error": error, "model_sha256": sha(directory / "lightgbm.txt")})
    return sample


def export_case(folder, year):
    daily = pd.read_csv(folder / "engine_daily.csv")
    _, spot = fold_sources(year)
    for symbol, col in (("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")):
        ref = pd.read_csv(spot / f"{symbol}_{year}.csv")
        if list(daily.timestamp) != list(ref.timestamp):
            raise ValueError("Benchmark calendar mismatch")
        daily[col] = ref.strategy_nav.to_numpy()
    validated = validate_daily(daily)
    if not (validated.index.year == year).all() or len(daily) != 365:
        raise ValueError("Year scope/snapshot mismatch")
    daily.to_csv(folder / "daily.csv", index=False)
    metrics, monthly = performance_tables(validated)
    metrics.to_csv(folder / "metrics.csv")
    monthly.to_csv(folder / "monthly_returns.csv")
    fills = pd.read_csv(folder / "fills.csv")
    funding = pd.read_csv(folder / "funding.csv")
    if not np.allclose(daily.strategy_nav, daily.cash_usdt+daily.unrealized_usdt, rtol=0, atol=.01):
        raise ValueError("Marked equity reconciliation failed")
    for name, expected in (("commissions_usdt", fills.commission_usdt.sum()),
                           ("funding_cashflow_usdt", funding.cashflow_usdt.sum()),
                           ("traded_notional_usdt", fills.notional_usdt.sum())):
        if abs(daily[name].sum()-expected) > .001:
            raise ValueError("Fee/funding/notional reconciliation failed")
    times = pd.to_datetime(fills.timestamp_ns, unit="ns", utc=True)
    if not (times.dt.year == year).all() or not times.dt.hour.isin([2, 23]).all():
        raise ValueError("Unexpected fill time")
    engine = json.loads((folder / "engine_summary.json").read_text())
    if not engine["success"] or abs(engine["ledger_error_usdt"]) > .01:
        raise ValueError("Final engine ledger mismatch")
    best = monthly.strategy_nav.idxmax()
    cash = pd.Series(daily.strategy_nav.diff().fillna(0).to_numpy(), index=validated.index)
    cash = cash.resample(pd.offsets.MonthEnd()).sum()
    total = float(cash.sum())
    other = float((1+monthly.strategy_nav.drop(best)).prod()-1)
    result = {**metrics.loc["strategy_nav"].to_dict(), "traded_notional": float(fills.notional_usdt.sum()),
              "fees": float(fills.commission_usdt.sum()), "funding": float(funding.cashflow_usdt.sum()),
              "best_month": str(best), "best_month_return": float(monthly.loc[best, "strategy_nav"]),
              "best_month_cash_share": float(cash.loc[best]/total) if total > 0 else None,
              "other_months_compounded_return": other, "concentrated_positive_year": bool(total > 0 and other <= 0),
              "financial_sha256": engine["financial_sha256"], "fills": len(fills)}
    write(folder / "diagnostic_metrics.json", result)
    return result


def pairwise_gates(table):
    rows = []
    primary = table[table.slippage_bps == 5].set_index(["year", "config"])
    for config in list(CONFIGS)[1:]:
        changes = []
        for year in (2022, 2023):
            case, base = primary.loc[(year, config)], primary.loc[(year, "A_weekly")]
            stress = table[(table.year == year) & (table.config == config) & (table.slippage_bps == 10)].iloc[0]
            row = {"config": config, "year": year, "delta_return": case.total_return-base.total_return,
                   "delta_sharpe": case.Sharpe_rf0-base.Sharpe_rf0, "delta_MDD": case.MDD-base.MDD,
                   "notional_ratio_to_A": case.traded_notional/base.traded_notional,
                   "execution_gate_this_year": bool(case.total_return > 0 and case.Sharpe_rf0 > base.Sharpe_rf0
                       and case.MDD >= base.MDD and case.traded_notional < base.traded_notional),
                   "nonpositive_stress_return": bool(stress.total_return <= 0)}
            rows.append(row)
            changes.append(row["delta_sharpe"])
        for row in rows[-2:]:
            row["consistent_sharpe_improvement"] = all(v > 0 for v in changes)
            row["consistent_sharpe_decline"] = all(v < 0 for v in changes)
    return pd.DataFrame(rows)


def run(output):
    prepared = json.loads((PREPARED / "manifest.json").read_text())
    if any(sha(PREPARED / name) != digest for name, digest in prepared["output_hashes"].items()):
        raise ValueError("Prepared inputs changed")
    sources = {str(PREPARED / "manifest.json"): sha(PREPARED / "manifest.json")}
    for year in (2022, 2023):
        results, spot = fold_sources(year)
        meta = json.loads((spot / "summary.json").read_text())
        if any(sha(spot / name) != digest for name, digest in meta["output_hashes"].items()):
            raise ValueError("Spot cache changed")
        for name in ("lightgbm.txt", "training_samples.parquet", "validation_predictions.parquet"):
            path = results / "model" / name
            sources[str(path)] = sha(path)
        for bps in (5, 10):
            folder = results / "lightgbm_validation" / f"slippage_{bps}bps"
            for name in ("engine_summary.json", "engine_daily.csv", "fills.csv", "funding.csv", "targets.csv"):
                sources[str(folder / name)] = sha(folder / name)
        sources[str(spot / "summary.json")] = sha(spot / "summary.json")
    contract = {"script_sha256": sha(Path(__file__)), "rules_sha256": sha(ROOT / "scripts/strategy_adjustment_rules.py"),
                "engine_sha256": sha(ROOT / "scripts/first_development_engine.py"), "configs": CONFIGS,
                "registration_sha256": sha(ROOT / "experiments/010_bounded_strategy_adjustments.md"),
                "sources": sources, "runtime": {p: version(p) for p in ("nautilus_trader", "lightgbm", "shap", "pandas", "numpy")}}
    output.mkdir(parents=True, exist_ok=True)
    if (output / "run_contract.json").exists() and json.loads((output / "run_contract.json").read_text()) != contract:
        raise ValueError("Output bound to different contract: choose new --output")
    write(output / "run_contract.json", contract)
    frame = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    if frame.duplicated(["decision_date", "instrument_id"]).any() or (frame.feature_cutoff_ms >= 1704067200000).any():
        raise ValueError("Scope or feature key failure")
    data = HistoricalData(PREPARED)
    rows, replay_hashes = [], {}
    for year in (2022, 2023):
        original = full_model(frame, year)
        events = data.events(year, end_year=year)
        for config, settings in CONFIGS.items():
            print(f"Prepare {year}/{config}", flush=True)
            if config in ("F_no_momentum", "G_no_funding", "H_no_imbalance"):
                sample = ablated_model(frame, year, config, output / "models" / str(year) / config)
            else:
                sample = original.copy()
                if config == "E_funding_only":
                    sample["score"] = -sample.funding7
            portfolio, audit = portfolio_schedule(sample, year, weeks=settings["weeks"], buffer=settings["buffer"])
            write(output / str(year) / config / "schedule.json", {"weights": portfolio, "audit": audit})
            if config == "A_weekly":
                old_results, _ = fold_sources(year)
                targets = pd.read_csv(old_results / "lightgbm_validation/slippage_5bps/targets.csv")
                for day, group in targets.groupby("decision_date"):
                    expected = dict(zip(group[group.weight != 0].instrument_id, group[group.weight != 0].weight, strict=True))
                    if portfolio.get(day) != expected:
                        raise ValueError("Reference schedule differs from cached A")
            for bps in (5, 10):
                folder = output / str(year) / config / f"slippage_{bps}bps"
                if config == "A_weekly":
                    old_results, _ = fold_sources(year)
                    shutil.copytree(old_results / "lightgbm_validation" / f"slippage_{bps}bps", folder, dirs_exist_ok=True)
                else:
                    print(f"Simulate {year}/{config}/{bps}bps", flush=True)
                    simulate(data, events, portfolio, folder, bps=bps)
                result = export_case(folder, year)
                rows.append({"year": year, "config": config, "stage": settings["stage"], "slippage_bps": bps,
                             "cached_reference": config == "A_weekly", **result})
                pd.DataFrame(rows).to_csv(output / "all_runs.csv", index=False)
                if config == "B_buffer" and bps == 5:
                    _, replay = simulate(data, events, portfolio, output / str(year) / config / "primary_replay", bps=5)
                    if replay["financial_sha256"] != result["financial_sha256"]:
                        raise ValueError("Buffer replay mismatch")
                    replay_hashes[str(year)] = replay["financial_sha256"]
                print(json.dumps(rows[-1]), flush=True)
    table = pd.DataFrame(rows)
    pairs = pairwise_gates(table)
    pairs.to_csv(output / "paired_comparisons.csv", index=False)
    preferred = [config for config in ("B_buffer", "C_two_week", "D_four_week")
                 if pairs[pairs.config == config].execution_gate_this_year.all()]
    if any(sha(Path(path)) != digest for path, digest in sources.items()):
        raise ValueError("Source inputs changed during run")
    write(output / "summary.json", {"success": True, "registered_cases": len(rows), "new_simulations": 28,
          "cached_references": 4, "replay_hashes": replay_hashes, "new_ablation_fits": 6,
          "supported_execution_candidates": preferred, "development_years": [2022, 2023],
          "sealed_2024_and_final_OOS_inspected": False, "paper_or_live_ready": False})
    print(json.dumps({"success": True, "cases": len(rows), "supported_execution_candidates": preferred}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE / "results")
    run(parser.parse_args().output)
