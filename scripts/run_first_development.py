"""Run Experiment005 end-to-end: fixed training, SHAP, engine, costs and reports."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from audit_development_continuity import sha
from development_continuity_rules import mondays
from first_development_engine import HistoricalData, simulate
from prepare_first_development import END, FEATURES, OUTPUT, ROOT

sys.path.insert(0, str(ROOT / "src"))
from momentum_data.backtest_analysis import plot_development, validate_daily  # noqa: E402

RESULTS = ROOT / "data/interim/first_development/v20261121_001/results_v003"
MODEL_CACHE = ROOT / "data/interim/first_development/v20261121_001/results/model"
SPOT = ROOT / "data/interim/first_development/v20261121_001/spot_benchmarks"
PARAMS = dict(n_estimators=100, learning_rate=.03, num_leaves=7, max_depth=3,
              min_child_samples=100, reg_lambda=10., subsample=1., colsample_bytree=1.,
              random_state=42, deterministic=True, force_col_wise=True, n_jobs=1, verbosity=-1)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def training_rows(frame):
    cutoff = 1640995200000
    return frame[(frame.feature_cutoff_ms < cutoff) & (frame.label_available_ms < cutoff)
                 & frame.label.notna()].copy()


def portfolio_schedule(frame, score, start_year):
    schedule = {}
    for day in mondays():
        if day.year < start_year:
            continue
        sample = frame[frame.decision_date == day.isoformat()].sort_values(
            [score, "instrument_id"], ascending=[False, True], kind="stable")
        if len(sample) < 20:
            schedule[day.isoformat()] = {}
            continue
        longs = sample.instrument_id.iloc[:5]
        shorts = sample.instrument_id.iloc[-5:]
        schedule[day.isoformat()] = {**dict.fromkeys(longs, .1), **dict.fromkeys(shorts, -.1)}
    return schedule


def model_scores(features, output, cache=None):
    train = training_rows(features)
    validation = features[features.feature_cutoff_ms >= 1640995200000].copy()
    if len(train) < 500 or (train.label_available_ms >= 1640995200000).any():
        raise ValueError("Invalid training size or unpurged boundary")
    output.mkdir(parents=True, exist_ok=True)
    reused = False
    if cache and (cache / "model_summary.json").exists():
        metadata = json.loads((cache / "model_summary.json").read_text())
        if metadata["parameters"] != PARAMS or metadata["features"] != FEATURES:
            raise ValueError("Cached model does not match frozen parameters")
        previous_train = pd.read_parquet(cache / "training_samples.parquet")
        pd.testing.assert_frame_equal(train.reset_index(drop=True), previous_train.reset_index(drop=True), check_dtype=False)
        previous_validation = pd.read_parquet(cache / "validation_predictions.parquet")
        booster = lgb.Booster(model_file=str(cache / "lightgbm.txt"))
        if not np.allclose(booster.predict(previous_validation[FEATURES]), previous_validation.score, rtol=0, atol=1e-12):
            raise ValueError("Cached model/prediction consistency failed")
        shutil.copyfile(cache / "lightgbm.txt", output / "lightgbm.txt")
        reused = True
    else:
        model = lgb.LGBMRegressor(**PARAMS)
        model.fit(train[FEATURES], train.label)
        booster = model.booster_
        booster.save_model(str(output / "lightgbm.txt"))
    validation["score"] = booster.predict(validation[FEATURES])
    train.to_parquet(output / "training_samples.parquet", index=False)
    validation.to_parquet(output / "validation_predictions.parquet", index=False)
    explainer = shap.TreeExplainer(booster, feature_perturbation="tree_path_dependent")
    values = np.asarray(explainer.shap_values(validation[FEATURES], check_additivity=True))
    base = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    error = float(np.max(np.abs(values.sum(axis=1) + base - validation.score.to_numpy())))
    if not np.isfinite(values).all() or error > 1e-6:
        raise ValueError("SHAP additivity or finiteness check failed")
    attribution = validation[["instrument_id", "decision_date", "score"]].copy()
    for i, name in enumerate(FEATURES):
        attribution[f"shap_{name}"] = values[:, i]
    attribution["expected_value"] = base
    attribution.to_csv(output / "shap_values.csv", index=False)
    importance = pd.Series(np.abs(values).mean(axis=0), index=FEATURES, name="mean_absolute_SHAP").sort_values()
    importance.to_csv(output / "shap_importance.csv")
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    importance.plot.barh(ax=ax, color="#2a9d8f")
    ax.set(title="2022 validation SHAP — model attribution, not causality", xlabel="Mean absolute SHAP (return units)")
    fig.savefig(output / "shap_importance.png", dpi=160)
    plt.close(fig)
    metadata = {"train_rows": len(train), "validation_rows": len(validation),
                "latest_training_label_available_ms": int(train.label_available_ms.max()),
                "validation_start_ms": int(validation.feature_cutoff_ms.min()),
                "fit_count": 1, "parameters": PARAMS, "features": FEATURES,
                "model_reused": reused, "new_fit_count": 0 if reused else 1,
                "frozen_model_sha256": sha(output / "lightgbm.txt"),
                "shap_additivity_max_error": error, "OOS_performance_inspected": False}
    write(output / "model_summary.json", metadata)
    return validation, metadata


def export_report(frame, benchmarks, directory, year, prepared_hash):
    daily = frame.merge(benchmarks["BTCUSDT"][["timestamp", "strategy_nav"]].rename(
        columns={"strategy_nav": "btc_nav"}), on="timestamp", validate="one_to_one").merge(
        benchmarks["ETHUSDT"][["timestamp", "strategy_nav"]].rename(columns={"strategy_nav": "eth_nav"}),
        on="timestamp", validate="one_to_one")
    validated = validate_daily(daily)
    daily.to_csv(directory / "daily.csv", index=False)
    manifest = {"report_type": "historical_development", "OOS_performance_inspected": False,
                "start_inclusive": f"{year}-01-01T00:00:00Z", "end_exclusive": "2023-01-01T00:00:00Z",
                "last_valuation": "2022-12-31T00:00:00Z", "currency": "USDT", "external_cashflows": "none",
                "nav_basis": "marked_equity_net_of_fees_and_funding",
                "benchmark_definition": "BTC/ETH actual spot-price passive fixed-unit hold; 5bps adverse fills and 0.001 spot taker; no funding/leverage",
                "benchmark_implementation": "passive quote-budget/fixed-unit accounting identity, not Nautilus spot-exchange simulation",
                "spot_sources_sha256": sha(SPOT / "sources.json"),
                "prepared_manifest_sha256": prepared_hash, "certified_point_in_time_universe": False,
                "identity_continuity": "conditional same-symbol 2020-to-2022 research assumption",
                "execution": "01UTC known sizing, 02UTC prior-hour VWAP synthetic fills; fractional lots",
                "funding": "archive events; latest completed mark-hour settlement proxy, <=2h old",
                "fees": "current-cost VIP0 reference taker 0.0005, no BNB; not verified historical schedule",
                "liquidation_and_exchange_lot_filters_verified": False,
                "registration": "experiments/005_first_historical_development_run.md"}
    write(directory / "manifest.json", manifest)
    fig, metrics, monthly = plot_development(validated)
    fig.suptitle(f"{year}–2022 CONDITIONAL DEVELOPMENT — BTC/ETH spot-price hold benchmarks")
    fig.savefig(directory / "dashboard.png", dpi=160)
    plt.close(fig)
    metrics.to_csv(directory / "metrics.csv")
    monthly.to_csv(directory / "monthly_returns.csv")
    return metrics


def run(prepared, output, primary_only=False):
    metadata = json.loads((prepared / "manifest.json").read_text())
    if any(sha(prepared / name) != digest for name, digest in metadata["output_hashes"].items()):
        raise ValueError("Prepared data hashes changed")
    spot_summary = json.loads((SPOT / "summary.json").read_text())
    if any(sha(SPOT / name) != digest for name, digest in spot_summary["output_hashes"].items()):
        raise ValueError("Spot benchmark outputs changed")
    output.mkdir(parents=True, exist_ok=True)
    contract = {"prepared_manifest_sha256": sha(prepared / "manifest.json"),
                "script_sha256": sha(Path(__file__)), "engine_sha256": sha(ROOT / "scripts/first_development_engine.py"),
                "registration_sha256": sha(ROOT / "experiments/005_first_historical_development_run.md"),
                "benchmark_correction_sha256": sha(ROOT / "experiments/006_spot_benchmark_correction.md"),
                "trade_repair_registration_sha256": sha(ROOT / "experiments/007_execution_trade_source_repair.md"),
                "spot_benchmark_hashes": spot_summary["output_hashes"],
                "spot_sources_sha256": sha(SPOT / "sources.json"),
                "cached_model_sha256": sha(MODEL_CACHE / "lightgbm.txt"),
                "primary_only": primary_only,
                "runtime": {p: version(p) for p in ("nautilus_trader", "lightgbm", "shap", "numpy", "pandas", "pyarrow")}}
    existing = output / "run_contract.json"
    if existing.exists() and json.loads(existing.read_text()) != contract:
        raise ValueError("Run version bound to different code/input/runtime: choose new --output")
    write(existing, contract)
    features = pd.read_parquet(prepared / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    if (features.feature_cutoff_ms >= END).any():
        raise ValueError("Feature window exceeds registered development scope")
    print("Verifying/reusing fixed 2021 model and 2022 validation SHAP", flush=True)
    validation, model_metadata = model_scores(features, output / "model", MODEL_CACHE)
    data = HistoricalData(prepared)
    models = [("momentum_baseline", features, "momentum60", 2021),
              ("lightgbm_validation", validation, "score", 2022)]
    rows = []
    for name, sample, score, year in models:
        if primary_only and year == 2021:
            continue
        print(f"Building {year} market/funding event feed", flush=True)
        events = data.events(year)
        schedule = portfolio_schedule(sample, score, year)
        benchmarks = {}
        for symbol in ("BTCUSDT", "ETHUSDT"):
            benchmarks[symbol] = pd.read_csv(SPOT / f"{symbol}_{year}.csv")
        cases = (5,) if primary_only else (0, 2, 5, 10)
        for bps in cases:
            print(f"Simulating {name}, extra slippage={bps}bps", flush=True)
            directory = output / name / f"slippage_{bps}bps"
            daily, summary = simulate(data, events, schedule, directory, bps=bps)
            metrics = export_report(daily, benchmarks, directory, year, contract["prepared_manifest_sha256"])
            primary_metrics = metrics.loc["strategy_nav"].to_dict()
            rows.append({"model": name, "start_year": year, "slippage_bps": bps,
                         **primary_metrics, **summary})
            pd.DataFrame(rows).to_csv(output / "all_runs.csv", index=False)
            print(json.dumps(rows[-1]), flush=True)
            if year == 2022 and bps == 5:
                print("Replaying primary 2022 case for financial determinism", flush=True)
                _, repeat = simulate(data, events, schedule, output / name / "primary_replay", bps=bps)
                if summary["financial_sha256"] != repeat["financial_sha256"]:
                    raise ValueError("Primary financial outputs not deterministic")
    report = {"success": True, "historical_backtest_executed": True, "PnL_computed": True,
              "model_fitted": True, "model_fit_count": 1, "SHAP_computed": True,
              "model": model_metadata, "registered_runs_completed": len(rows),
              "primary_replay_identical": True, "certified_point_in_time_universe": False,
              "paper_or_live_ready": False, "OOS_performance_inspected": False}
    write(output / "summary.json", report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=OUTPUT.parent / "prepared_v003")
    parser.add_argument("--output", type=Path, default=RESULTS)
    parser.add_argument("--primary-only", action="store_true", help="Engineering/debug primary case, still a logged trial")
    args = parser.parse_args()
    run(args.prepared, args.output, args.primary_only)
