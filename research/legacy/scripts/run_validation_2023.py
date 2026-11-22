"""Experiment009: one expanding fit, frozen2023 validation, eight engine cases."""

import json
import sys
from importlib.metadata import version
from pathlib import Path

import lightgbm as lgb
import matplotlib
import numpy as np
import pandas as pd
import shap
from audit_development_continuity import sha
from build_validation_2023_spot import SPOT
from first_development_engine import HistoricalData, simulate
from prepare_validation_2023 import BASE, END, FEATURES, PREPARED, ROOT, START, calendar, write
from run_first_development import PARAMS

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(ROOT / "src"))
from momentum_data.backtest_analysis import plot_development, validate_daily  # noqa: E402

RESULTS = BASE / "results"


def training_rows(frame):
    return frame[(frame.feature_cutoff_ms < START) & (frame.label_available_ms < START)
                 & frame.label.notna()].copy()


def schedule(frame, score):
    result = {}
    for day in calendar():
        sample = frame[frame.decision_date == day.isoformat()].sort_values(
            [score, "instrument_id"], ascending=[False, True], kind="stable")
        result[day.isoformat()] = ({**dict.fromkeys(sample.instrument_id.iloc[:5], .1),
                                   **dict.fromkeys(sample.instrument_id.iloc[-5:], -.1)} if len(sample) >= 20 else {})
    return result


def model_scores(features):
    out = RESULTS / "model"
    out.mkdir(parents=True, exist_ok=True)
    training = training_rows(features)
    validation = features[(features.feature_cutoff_ms >= START) & (features.feature_cutoff_ms < END)].copy()
    if len(training) < 500 or not validation.label.isna().all():
        raise ValueError("Invalid training or validation labels unexpectedly present")
    if (out / "model_summary.json").exists():
        meta = json.loads((out / "model_summary.json").read_text())
        pd.testing.assert_frame_equal(training, pd.read_parquet(out / "training_samples.parquet"))
        if meta["parameters"] != PARAMS or sha(out / "lightgbm.txt") != meta["model_sha256"]:
            raise ValueError("Frozen2023 model cache changed")
        booster = lgb.Booster(model_file=str(out / "lightgbm.txt"))
    else:
        model = lgb.LGBMRegressor(**PARAMS)
        model.fit(training[FEATURES], training.label)
        booster = model.booster_
        booster.save_model(str(out / "lightgbm.txt"))
    validation["score"] = booster.predict(validation[FEATURES])
    training.to_parquet(out / "training_samples.parquet", index=False)
    validation.to_parquet(out / "validation_predictions.parquet", index=False)
    explainer = shap.TreeExplainer(booster, feature_perturbation="tree_path_dependent")
    values = np.asarray(explainer.shap_values(validation[FEATURES], check_additivity=True))
    expected = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    error = float(np.max(np.abs(values.sum(axis=1)+expected-validation.score.to_numpy())))
    if not np.isfinite(values).all() or error > 1e-6:
        raise ValueError("2023SHAP verification failed")
    attributed = validation[["instrument_id", "decision_date", "score"]].copy()
    for i, feature in enumerate(FEATURES):
        attributed[f"shap_{feature}"] = values[:, i]
    attributed["expected_value"] = expected
    attributed.to_csv(out / "shap_values.csv", index=False)
    importance = pd.Series(np.abs(values).mean(axis=0), index=FEATURES, name="mean_absolute_SHAP").sort_values()
    importance.to_csv(out / "shap_importance.csv")
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    importance.plot.barh(ax=ax)
    ax.set(title="2023 validation SHAP (not causal PnL attribution)", xlabel="Mean absolute SHAP")
    fig.savefig(out / "shap_importance.png", dpi=150)
    plt.close(fig)
    meta = {"train_rows": len(training), "validation_rows": len(validation), "parameters": PARAMS,
            "features": FEATURES, "model_sha256": sha(out / "lightgbm.txt"), "fit_count": 1,
            "latest_training_label_available_ms": int(training.label_available_ms.max()),
            "training_end_exclusive_ms": START, "shap_additivity_max_error": error,
            "validation_labels_computed": False, "sealed_2024_and_final_OOS_inspected": False}
    write(out / "model_summary.json", meta)
    return validation, meta


def export_report(frame, folder, contract):
    daily = frame.copy()
    for symbol, name in (("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")):
        ref = pd.read_csv(SPOT / f"{symbol}_2023.csv")
        if list(ref.timestamp) != list(daily.timestamp):
            raise ValueError("Benchmark/strategy calendar mismatch")
        daily[name] = ref.strategy_nav.to_numpy()
    checked = validate_daily(daily)
    if checked.index.min() != pd.Timestamp("2023-01-01", tz="UTC") or checked.index.max() != pd.Timestamp("2023-12-31", tz="UTC"):
        raise ValueError("2023report boundary mismatch")
    daily.to_csv(folder / "daily.csv", index=False)
    fig, metrics, monthly = plot_development(checked)
    fig.suptitle("2023 FROZEN VALIDATION — conditional37-asset cohort; net of fees/funding")
    fig.savefig(folder / "dashboard.png", dpi=150)
    plt.close(fig)
    metrics.to_csv(folder / "metrics.csv")
    monthly.to_csv(folder / "monthly_returns.csv")
    write(folder / "manifest.json", {"report_type": "frozen_validation_2023",
          "start_inclusive": "2023-01-01T00:00:00Z", "end_exclusive": "2024-01-01T00:00:00Z",
          "last_valuation": "2023-12-31T00:00:00Z", "nav_basis": "marked_equity_net_of_fees_and_funding",
          "currency": "USDT", "external_cashflows": "none", "certified_point_in_time_universe": False,
          "sealed_2024_and_final_OOS_inspected": False, "contract": contract})
    return metrics, monthly


def verify_case(folder):
    daily = pd.read_csv(folder / "daily.csv")
    fills, funding = [pd.read_csv(folder / f"{name}.csv") for name in ("fills", "funding")]
    if not np.allclose(daily.strategy_nav, daily.cash_usdt+daily.unrealized_usdt, rtol=0, atol=.01):
        raise ValueError("NAV/cash/mark mismatch")
    for col, amount in (("commissions_usdt", fills.commission_usdt.sum()),
                        ("funding_cashflow_usdt", funding.cashflow_usdt.sum()),
                        ("traded_notional_usdt", fills.notional_usdt.sum())):
        if abs(daily[col].sum()-amount) > .001:
            raise ValueError("Daily ledger mismatch")
    timestamps = pd.to_datetime(fills.timestamp_ns, unit="ns", utc=True)
    if not timestamps.dt.hour.isin([2, 23]).all() or not (timestamps.dt.year == 2023).all():
        raise ValueError("Invalid fill time")
    engine = json.loads((folder / "engine_summary.json").read_text())
    if abs(engine["ledger_error_usdt"]) > .01:
        raise ValueError("Engine final reconciliation failed")


def run():
    prepared = json.loads((PREPARED / "manifest.json").read_text())
    spot = json.loads((SPOT / "summary.json").read_text())
    for folder, meta in ((PREPARED, prepared), (SPOT, spot)):
        if any(sha(folder / name) != digest for name, digest in meta["output_hashes"].items()):
            raise ValueError("Source cache integrity failure")
    contract = {"prepared_sha256": sha(PREPARED / "manifest.json"), "spot_sha256": sha(SPOT / "summary.json"),
                "registration_sha256": sha(ROOT / "experiments/009_frozen_2023_validation.md"),
                "script_sha256": sha(Path(__file__)), "engine_sha256": sha(ROOT / "scripts/first_development_engine.py"),
                "runtime": {p: version(p) for p in ("nautilus_trader", "lightgbm", "shap", "numpy", "pandas", "pyarrow")}}
    RESULTS.mkdir(parents=True, exist_ok=True)
    if (RESULTS / "run_contract.json").exists() and json.loads((RESULTS / "run_contract.json").read_text()) != contract:
        raise ValueError("Run version bound to different code/input/runtime")
    write(RESULTS / "run_contract.json", contract)
    features = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    if (features.feature_cutoff_ms >= END).any():
        raise ValueError("Out-of-scope features")
    print("Fit2021-2022 once; predict2023 and compute SHAP", flush=True)
    validation, model = model_scores(features)
    data = HistoricalData(PREPARED)
    events = data.events(2023, end_year=2023)
    rows, concentration = [], {}
    for name, score in (("lightgbm_validation", "score"), ("momentum_baseline", "momentum60")):
        portfolio = schedule(validation, score)
        for bps in (0, 2, 5, 10):
            print(f"Nautilus2023 {name} slippage={bps}bps", flush=True)
            folder = RESULTS / name / f"slippage_{bps}bps"
            daily, engine = simulate(data, events, portfolio, folder, bps=bps)
            metrics, monthly = export_report(daily, folder, contract)
            verify_case(folder)
            rows.append({"model": name, "slippage_bps": bps, **metrics.loc["strategy_nav"].to_dict(), **engine})
            pd.DataFrame(rows).to_csv(RESULTS / "all_runs.csv", index=False)
            if bps == 5:
                best = monthly.strategy_nav.idxmax()
                changes = daily.strategy_nav.diff().fillna(0)
                pnl = pd.Series(changes.to_numpy(), index=pd.to_datetime(daily.timestamp, utc=True)).resample(pd.offsets.MonthEnd()).sum()
                total = float(changes.sum())
                concentration[name] = {"best_month": str(best), "best_month_return": float(monthly.loc[best, "strategy_nav"]),
                    "best_month_cash_pnl": float(pnl.loc[best]),
                    "best_month_share_of_annual_cash_pnl": float(pnl.loc[best]/total) if total > 0 else None,
                    "other_months_compounded_return": float((1+monthly.strategy_nav.drop(best)).prod()-1),
                    "concentration_dependent": bool(total > 0 and (1+monthly.strategy_nav.drop(best)).prod() <= 1)}
                if name == "lightgbm_validation":
                    _, repeat = simulate(data, events, portfolio, RESULTS / name / "primary_replay", bps=5)
                    if repeat["financial_sha256"] != engine["financial_sha256"]:
                        raise ValueError("Financial replay mismatch")
            print(json.dumps(rows[-1]), flush=True)
    primary = pd.DataFrame(rows).query("slippage_bps == 5").set_index("model")
    ml, mom = primary.loc["lightgbm_validation"], primary.loc["momentum_baseline"]
    report = {"success": True, "registered_runs_completed": len(rows), "model": model,
              "primary_replay_identical": True, "primary_results": primary.to_dict("index"),
              "concentration": concentration, "evidence_gates": {
                  "positive_net_return_and_sharpe": bool(ml.total_return > 0 and ml.Sharpe_rf0 > 0),
                  "beats_matched_momentum_return_and_sharpe": bool(ml.total_return > mom.total_return and ml.Sharpe_rf0 > mom.Sharpe_rf0)},
              "certified_point_in_time_universe": False, "paper_or_live_ready": False,
              "validation_2023_performance_inspected": True, "sealed_2024_and_final_OOS_inspected": False}
    write(RESULTS / "summary.json", report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    run()
