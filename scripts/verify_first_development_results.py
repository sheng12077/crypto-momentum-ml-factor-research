"""Independent report/source/ledger checks for completed registered development runs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from audit_development_continuity import sha

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/first_development/v20261121_001"
RUN = BASE / "results_v003"


def main():
    summary = json.loads((RUN / "summary.json").read_text())
    if not summary["success"] or summary["registered_runs_completed"] != 8 or not summary["primary_replay_identical"]:
        raise ValueError("Incomplete registered run set")
    if summary["OOS_performance_inspected"] or summary["certified_point_in_time_universe"]:
        raise ValueError("Incorrect scope claim")
    spot = BASE / "spot_benchmarks"
    meta = json.loads((spot / "summary.json").read_text())
    if any(sha(spot / name) != digest for name, digest in meta["output_hashes"].items()):
        raise ValueError("Spot benchmark source outputs changed")
    training = pd.read_parquet(RUN / "model/training_samples.parquet")
    original = pd.read_parquet(BASE / "results/model/training_samples.parquet")
    pd.testing.assert_frame_equal(training, original, check_dtype=False, check_exact=True)
    if (training.label_available_ms >= 1640995200000).any():
        raise ValueError("Unpurged training label")
    if sha(RUN / "model/lightgbm.txt") != sha(BASE / "results/model/lightgbm.txt"):
        raise ValueError("Frozen model changed after data repair")
    attribution = pd.read_csv(RUN / "model/shap_values.csv")
    features = pd.read_parquet(BASE / "prepared_v003/features.parquet")
    coverage = features.groupby("decision_date").size()
    coverage_report = {"weekly_candidate_minimum": int(coverage.min()),
                       "weekly_candidate_median": float(coverage.median()),
                       "weekly_candidate_maximum": int(coverage.max()),
                       "validation_2022_rows": int((features.feature_cutoff_ms >= 1640995200000).sum()),
                       "feature_rows": len(features),
                       "source": "prepared_v003/features.parquet"}
    (RUN / "final_coverage.json").write_text(json.dumps(coverage_report, indent=2))
    residual = (attribution.filter(regex="^shap_").sum(axis=1)
                + attribution.expected_value - attribution.score).abs().max()
    if residual > 1e-6:
        raise ValueError("SHAP additivity failed")
    counts = []
    for model, year in [("momentum_baseline", 2021), ("lightgbm_validation", 2022)]:
        for bps in (0, 2, 5, 10):
            folder = RUN / model / f"slippage_{bps}bps"
            daily = pd.read_csv(folder / "daily.csv")
            fills = pd.read_csv(folder / "fills.csv")
            funding = pd.read_csv(folder / "funding.csv")
            report = json.loads((folder / "engine_summary.json").read_text())
            if abs(report["ledger_error_usdt"]) > .01:
                raise ValueError("Cash/realized/funding reconciliation failure")
            if not np.allclose(daily.strategy_nav, daily.cash_usdt + daily.unrealized_usdt, rtol=0, atol=.01):
                raise ValueError("Marked equity does not reconcile")
            for column, expected in [
                ("commissions_usdt", fills.commission_usdt.sum()),
                ("funding_cashflow_usdt", funding.cashflow_usdt.sum()),
                ("traded_notional_usdt", fills.notional_usdt.sum())]:
                if abs(daily[column].sum() - expected) > .001:
                    raise ValueError(f"Daily ledger totals differ:{column}")
            for symbol, column in [("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")]:
                reference = pd.read_csv(spot / f"{symbol}_{year}.csv")
                if list(daily.timestamp) != list(reference.timestamp) or not np.allclose(
                        daily[column], reference.strategy_nav, rtol=0, atol=1e-8):
                    raise ValueError("Benchmark calendar/NAV mismatch")
            timestamps = pd.to_datetime(fills.timestamp_ns, unit="ns", utc=True)
            if not timestamps.dt.hour.isin([2, 23]).all():
                raise ValueError("Fill before registered execution availability")
            if not np.isfinite(daily.strategy_nav).all() or (daily.strategy_nav <= 0).any():
                raise ValueError("Invalid reported NAV")
            counts.append({"model": model, "bps": bps, "daily_rows": len(daily), "fills": len(fills)})
    report = {"success": True, "verified_registered_cases": len(counts),
              "cases": counts, "training_unchanged": True, "frozen_model_unchanged": True,
              "SHAP_additivity_error": float(residual), "OOS_performance_inspected": False,
              "final_coverage": coverage_report,
              "output_hashes": {str(p.relative_to(RUN)): sha(p) for p in RUN.rglob("*")
                                if p.is_file() and p.name != "independent_verification.json"}}
    (RUN / "independent_verification.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in report.items() if k not in ("output_hashes", "cases")}))


if __name__ == "__main__":
    main()
