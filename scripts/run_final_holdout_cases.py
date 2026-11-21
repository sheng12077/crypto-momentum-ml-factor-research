"""Two frozen annual fits, twelve isolated/continuous Nautilus cases and three replays."""
import json
import shutil
from datetime import UTC, datetime

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from audit_development_continuity import sha
from build_final_holdout_spot import SPOT
from final_holdout_common import (
    BASE, DAY, FEATURES, PREPARED, ROOT, STOP, WINDOWS, bind, checked_manifest,
    code_contract, matured_training, ms, schedules, window_schedule, write,
)
from final_holdout_engine import FinalHistoricalData, simulate
from run_first_development import PARAMS

import sys
sys.path.insert(0, str(ROOT / "src"))
from momentum_data.backtest_analysis import performance_tables, validate_daily

RESULTS = BASE / "results"
PRODUCTS = ["engine_daily.csv", "fills.csv", "funding.csv", "targets.csv", "engine_summary.json",
            "daily.csv", "metrics.csv", "monthly_returns.csv", "diagnostics.json"]


def samples(year):
    cutoff = ms(f"{year}-01-01")
    frame = pd.read_parquet(PREPARED / "features.parquet")
    # Project/filter before touching any potential label exit prices.
    trades = pd.read_parquet(PREPARED / "trade.parquet", filters=[("bar_open_ms", "<", cutoff)])
    training = matured_training(frame, trades, cutoff)
    stop = min(ms(f"{year+1}-01-01"), STOP)
    validation = frame[(frame.feature_cutoff_ms >= cutoff) & (frame.feature_cutoff_ms < stop)].copy()
    return training, validation.sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)


def model_scores(year):
    folder = RESULTS / f"models/{year}"
    train, validation = samples(year)
    if len(train) < 500 or validation.empty or not validation.label.isna().all():
        raise ValueError("Invalid training/forecast samples")
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "model_summary.json").exists():
        meta = checked_manifest(folder, "model_summary.json")
        pd.testing.assert_frame_equal(train.reset_index(drop=True), pd.read_parquet(
            folder / "training_samples.parquet").reset_index(drop=True), check_exact=True)
        if meta["parameters"] != PARAMS:
            raise ValueError("Frozen model parameters changed")
        return pd.read_parquet(folder / "predictions.parquet")
    partial = [p for p in folder.iterdir() if p.is_file()]
    if partial:
        archive = folder / "attempts" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        archive.mkdir(parents=True, exist_ok=False)
        for prior in partial:
            shutil.copyfile(prior, archive / prior.name)
    write(folder / "fit_attempt.json", {"year": year, "parameters": PARAMS,
        "started_at": datetime.now(UTC).isoformat()})
    estimator = lgb.LGBMRegressor(**PARAMS)
    estimator.fit(train[FEATURES], train.label)
    booster = estimator.booster_
    booster.save_model(str(folder / "lightgbm.txt"))
    validation["score"] = booster.predict(validation[FEATURES])
    explainer = shap.TreeExplainer(booster, feature_perturbation="tree_path_dependent")
    values = np.asarray(explainer.shap_values(validation[FEATURES], check_additivity=True))
    expected = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    error = float(np.max(np.abs(values.sum(axis=1)+expected-validation.score.to_numpy())))
    if not np.isfinite(values).all() or error > 1e-6:
        raise ValueError("SHAP additivity failed")
    attributed = validation[["decision_date", "instrument_id", "score"]].copy()
    for i, feature in enumerate(FEATURES):
        attributed[f"shap_{feature}"] = values[:, i]
    attributed["expected_value"] = expected
    attributed.to_csv(folder / "shap_values.csv", index=False)
    pd.Series(np.abs(values).mean(axis=0), index=FEATURES, name="mean_absolute_SHAP").to_csv(
        folder / "shap_importance.csv")
    train.to_parquet(folder / "training_samples.parquet", index=False)
    validation.to_parquet(folder / "predictions.parquet", index=False)
    write(folder / "model_summary.json", {"fit_count": 1, "year": year, "train_rows": len(train),
        "prediction_rows": len(validation), "parameters": PARAMS, "features": FEATURES,
        "training_cutoff_ms": ms(f"{year}-01-01"), "latest_label_available_ms": int(train.label_available_ms.max()),
        "shap_additivity_max_error": error, "prediction_year_labels_computed": False,
        "output_hashes": {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != "model_summary.json"}})
    return validation


def read_ledger(folder, name):
    columns = {"fills": ["timestamp_ns", "instrument_id", "side", "quantity", "price", "commission_usdt", "notional_usdt"],
               "funding": ["timestamp_ns", "instrument_id", "signed_quantity", "cashflow_usdt"],
               "targets": ["decision_date", "instrument_id", "weight", "target_quantity"]}
    try:
        return pd.read_csv(folder / f"{name}.csv")
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns[name])


def export_case(folder, name):
    daily = pd.read_csv(folder / "engine_daily.csv")
    for symbol, column in (("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")):
        reference = pd.read_csv(SPOT / f"{symbol}_{name}.csv")
        if list(reference.timestamp) != list(daily.timestamp):
            raise ValueError("Spot/strategy calendar mismatch")
        daily[column] = reference.strategy_nav.to_numpy()
    data = validate_daily(daily)
    start, stop = WINDOWS[name]
    expected = pd.date_range(pd.Timestamp(start, unit="ms", tz="UTC"),
                             pd.Timestamp(stop-DAY, unit="ms", tz="UTC"), freq="D")
    if not data.index.equals(expected):
        raise ValueError("Snapshot boundary mismatch")
    if not np.allclose(daily.strategy_nav, daily.cash_usdt+daily.unrealized_usdt, atol=.01, rtol=0):
        raise ValueError("NAV/cash/unrealized mismatch")
    fills, funding = [read_ledger(folder, p) for p in ("fills", "funding")]
    for column, amount in (("commissions_usdt", fills.commission_usdt.sum()),
                           ("funding_cashflow_usdt", funding.cashflow_usdt.sum()),
                           ("traded_notional_usdt", fills.notional_usdt.sum())):
        if abs(daily[column].sum()-amount) > .001:
            raise ValueError("Daily ledger sums differ")
    times = pd.to_datetime(fills.timestamp_ns, unit="ns", utc=True)
    final = pd.Timestamp(stop-DAY-3_600_000, unit="ms", tz="UTC")
    if not times.dt.hour.isin([2, 23]).all() or (times > final).any() or (times < data.index[0]).any():
        raise ValueError("Unexpected fill timestamp")
    if name == "continuous" and ((times.dt.hour == 23) & (times != final)).any():
        raise ValueError("Continuous case flattened before registered endpoint")
    engine = json.loads((folder / "engine_summary.json").read_text())
    if not engine["success"] or abs(engine["ledger_error_usdt"]) > .01:
        raise ValueError("Engine financial reconciliation failed")
    daily.to_csv(folder / "daily.csv", index=False)
    metrics, monthly = performance_tables(data)
    metrics.to_csv(folder / "metrics.csv")
    monthly.to_csv(folder / "monthly_returns.csv")
    best = monthly.strategy_nav.idxmax()
    cash = pd.Series(daily.strategy_nav.diff().fillna(0).to_numpy(), index=data.index).resample(pd.offsets.MonthEnd()).sum()
    total = float(cash.sum())
    other = float((1+monthly.strategy_nav.drop(best)).prod()-1)
    result = {**metrics.loc["strategy_nav"].to_dict(), "fees": float(fills.commission_usdt.sum()),
        "funding": float(funding.cashflow_usdt.sum()), "traded_notional": float(fills.notional_usdt.sum()),
        "best_month": str(best), "best_month_cash_share": float(cash.loc[best]/total) if total > 0 else None,
        "other_months_compounded_return": other, "concentration_dependent": bool(total > 0 and other <= 0),
        "financial_sha256": engine["financial_sha256"]}
    write(folder / "diagnostics.json", result)
    return json.loads((folder / "diagnostics.json").read_text())


def verify_case(folder, key, contract_hash):
    meta = checked_manifest(folder, "_complete.json")
    if meta["key"] != key or meta["run_contract_sha256"] != contract_hash:
        raise ValueError("Case contract mismatch")
    return meta["result"]


def execute_case(data, events, portfolio, name, model, bps, replay=False):
    folder = RESULTS / f"{name}/{model}/" / ("primary_replay" if replay else f"slippage_{bps}bps")
    key = [name, model, bps, replay]
    contract_hash = sha(RESULTS / "run_contract.json")
    if (folder / "_complete.json").exists():
        return verify_case(folder, key, contract_hash)
    attempt = folder / "attempts" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True, exist_ok=True)
    write(attempt / "attempt.json", {"key": key, "run_contract_sha256": contract_hash})
    simulate(data, events, portfolio, attempt, bps=bps)
    result = export_case(attempt, name)
    for product in PRODUCTS:
        shutil.copyfile(attempt / product, folder / product)
    write(folder / "_complete.json", {"key": key, "run_contract_sha256": contract_hash,
        "result": result, "output_hashes": {p: sha(folder / p) for p in PRODUCTS}})
    return result


def gates(table):
    result = {}
    for name in WINDOWS:
        primary = table[(table.window == name) & (table.slippage_bps == 5)].set_index("model")
        ml, mom = primary.loc["lightgbm"], primary.loc["momentum60"]
        stress = table[(table.window == name) & (table.model == "lightgbm") & (table.slippage_bps == 10)].iloc[0]
        result[name] = {"positive_net_return_and_sharpe": bool(ml.total_return > 0 and ml.Sharpe_rf0 > 0),
            "positive_10bps_stress_return": bool(stress.total_return > 0),
            "beats_matched_momentum_return_and_sharpe": bool(ml.total_return > mom.total_return and ml.Sharpe_rf0 > mom.Sharpe_rf0)}
    return result


def run():
    bind(BASE / "code_contract.json", code_contract())
    prepared, spot = checked_manifest(PREPARED), checked_manifest(SPOT, "summary.json")
    contract = {"code_contract_sha256": sha(BASE / "code_contract.json"),
        "prepared_sha256": sha(PREPARED / "manifest.json"), "spot_sha256": sha(SPOT / "summary.json")}
    if prepared["code_contract_sha256"] != contract["code_contract_sha256"] or spot["code_contract_sha256"] != contract["code_contract_sha256"]:
        raise ValueError("Preparation contract differs")
    bind(RESULTS / "run_contract.json", contract)
    predictions = pd.concat([model_scores(y) for y in (2025, 2026)], ignore_index=True)
    plans = {"lightgbm": schedules(predictions), "momentum60": schedules(predictions, "momentum60")}
    data = FinalHistoricalData(PREPARED)
    rows = []
    for name, (start, stop) in WINDOWS.items():
        events = data.events_range(start, stop-DAY)
        for model, plan in plans.items():
            portfolio = window_schedule(plan, name)
            write(RESULTS / f"{name}/{model}/schedule.json", {"weights": portfolio})
            for bps in (5, 10):
                print(f"Nautilus {name}/{model}/{bps}bps", flush=True)
                result = execute_case(data, events, portfolio, name, model, bps)
                rows.append({"window": name, "model": model, "slippage_bps": bps, **result})
                pd.DataFrame(rows).to_csv(RESULTS / "all_runs.csv", index=False)
            if model == "lightgbm":
                replay = execute_case(data, events, portfolio, name, model, 5, True)
                primary = next(r for r in rows if r["window"] == name and r["model"] == model and r["slippage_bps"] == 5)
                if replay["financial_sha256"] != primary["financial_sha256"]:
                    raise ValueError("Primary financial replay mismatch")
    if code_contract() != json.loads((BASE / "code_contract.json").read_text()):
        raise ValueError("Inputs/code changed during execution")
    table = pd.DataFrame(rows)
    write(RESULTS / "summary.json", {"success": True, "registered_runs_completed": len(rows),
        "verified_replays": 3, "model_fits": 2, "evidence_gates": gates(table),
        "primary_results": table[table.slippage_bps == 5].to_dict("records"),
        "final_holdout_performance_computed": True, "paper_or_live_ready": False,
        "continuous_has_no_year_end_cash_reset": True, "prior_2024_validation_failed": True})
    print('{"success": true, "stage": "simulate", "completed_cases": 12, "replays": 3}')


if __name__ == "__main__":
    run()
