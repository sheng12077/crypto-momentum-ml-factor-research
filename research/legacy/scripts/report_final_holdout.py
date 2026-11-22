"""Verify saved final holdout results and render English tables, figures and notebook."""
import argparse
import json
import sys
from pathlib import Path

import lightgbm as lgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd
from audit_development_continuity import sha
from final_holdout_common import (
    BASE, FEATURES, OLD, PREPARED, ROOT, START, STOP, WINDOWS,
    checked_manifest, code_contract, schedules, window_schedule, write,
)
from run_final_holdout_cases import RESULTS, SPOT, gates, read_ledger, samples, terminal_blockers, verify_case
from momentum_data.backtest_analysis import performance_tables, plot_development, validate_daily

FIGURES = ROOT / "reports/figures/final_holdout"
TABLES = ROOT / "reports/tables/final_holdout"
NOTEBOOK = ROOT / "notebooks/final_holdout_results.ipynb"


def prepare_notebook():
    if NOTEBOOK.exists():
        return
    cells = [nbformat.v4.new_markdown_cell(
        "# Frozen final holdout: 2025 and January-October 2026\n\nExperiment 015. "
        "Original strategy unchanged; two annual expanding fits, no within-year tuning. "
        "2024 failed validation and remains part of the research record. "
        "Run `python scripts/run_final_holdout.py --stage all` first. This notebook reads saved results only. "
        "Unverified settlement cases are explicitly blocked; successful report generation does not mean complete market data."),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import Image, display\n"
            "ROOT = Path.cwd()\nif not (ROOT / 'scripts').exists():\n    ROOT = ROOT.parent\n"
            "BASE = ROOT / 'data/interim/final_holdout/v20261122_003'\n"
            "assert (BASE / 'results/verification.json').exists(), 'Complete the final holdout runner first.'\n"
            "display(pd.read_csv(ROOT / 'reports/tables/final_holdout/primary_metrics.csv'))"),
        nbformat.v4.new_markdown_cell(
            "## Separate windows and continuous trading\n\nStandalone runs reset cash. Continuous trading "
            "keeps positions and NAV across year-end and uses the 2026 model at its first scheduled decision. "
            "Do not compound standalone returns into a live curve. Final snapshots are at midnight on "
            "December 31, 2025 and October 31, 2026; the final civil day's return is omitted. "
            "CAGR and Sharpe are annualized; partial-period total returns are cumulative."),
        nbformat.v4.new_code_cell(
            "display(Image(filename=str(ROOT / 'reports/figures/final_holdout/continuous_dashboard.png')))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/final_holdout/continuous_year_slices.csv'))"),
        nbformat.v4.new_markdown_cell(
            "## All cases and monthly concentration\n\nPrimary extra slippage is 5 bps; 10 bps is "
            "mandatory stress. Monthly exclusion is descriptive and not a tradable strategy."),
        nbformat.v4.new_code_cell(
            "display(pd.DataFrame(json.loads((BASE / 'results/case_status.json').read_text())))\n"
            "display(pd.read_csv(BASE / 'results/all_runs.csv'))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/final_holdout/monthly_returns.csv'))\n"
            "display(Image(filename=str(ROOT / 'reports/figures/final_holdout/cost_stress.png')))") ,
        nbformat.v4.new_markdown_cell(
            "## Model attribution and verification\n\nSHAP explains predictions, not causal profits. "
            "Funding, hourly VWAP fills, fractional filters, retrospective identity evidence and historical "
            "liquidation remain conditional assumptions. No paper/live promotion is authorized."),
        nbformat.v4.new_code_cell(
            "display(Image(filename=str(ROOT / 'reports/figures/final_holdout/shap.png')))\n"
            "display(json.loads((BASE / 'results/summary.json').read_text())['evidence_gates'])\n"
            "display(json.loads((BASE / 'results/verification.json').read_text()))")]
    book = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {
        "display_name": "Python 3", "language": "python", "name": "python3"}})
    nbformat.write(book, NOTEBOOK)


def verify():
    if code_contract() != json.loads((BASE / "code_contract.json").read_text()):
        raise ValueError("Code/runtime/source contract changed")
    checked_manifest(PREPARED)
    checked_manifest(SPOT, "summary.json")
    summary = json.loads((RESULTS / "summary.json").read_text())
    if (summary["registered_runs_completed"]+len(summary.get("blocked_cases", [])) != 12
            or summary["verified_replays"] != 3 or not summary.get("all_planned_cases_accounted")):
        raise ValueError("Incomplete final holdout")
    old = pd.read_parquet(OLD / "features.parquet")
    frame = pd.read_parquet(PREPARED / "features.parquet")
    pd.testing.assert_frame_equal(frame[frame.feature_cutoff_ms < START].reset_index(drop=True),
                                  old.reset_index(drop=True), check_exact=True)
    if (frame.feature_cutoff_ms >= STOP).any():
        raise ValueError("Out-of-scope features")
    predictions = []
    for year in (2025, 2026):
        folder = RESULTS / f"models/{year}"
        meta = checked_manifest(folder, "model_summary.json")
        train, expected = samples(year)
        saved = pd.read_parquet(folder / "training_samples.parquet")
        pd.testing.assert_frame_equal(train.reset_index(drop=True), saved.reset_index(drop=True), check_exact=True)
        if (saved.label_available_ms >= meta["training_cutoff_ms"]).any():
            raise ValueError("Training label leakage")
        sample = pd.read_parquet(folder / "predictions.parquet")
        pd.testing.assert_frame_equal(sample.drop(columns="score"), expected, check_exact=True)
        booster = lgb.Booster(model_file=str(folder / "lightgbm.txt"))
        if not np.allclose(booster.predict(sample[FEATURES]), sample.score, rtol=0, atol=1e-12):
            raise ValueError("Model predictions mismatch")
        attributed = pd.read_csv(folder / "shap_values.csv")
        pd.testing.assert_frame_equal(attributed[["decision_date", "instrument_id"]],
                                      sample[["decision_date", "instrument_id"]], check_exact=True)
        error = (attributed.filter(regex="^shap_").sum(axis=1)+attributed.expected_value-sample.score).abs().max()
        if not np.isfinite(error) or error > 1e-6 or not sample.label.isna().all():
            raise ValueError("SHAP/forecast label verification failed")
        predictions.append(sample)
    predictions = pd.concat(predictions, ignore_index=True)
    plans = {"lightgbm": schedules(predictions), "momentum60": schedules(predictions, "momentum60")}
    rows, contract_hash = [], sha(RESULTS / "run_contract.json")
    for name in WINDOWS:
        for model in plans:
            expected = window_schedule(plans[model], name)
            actual = json.loads((RESULTS / f"{name}/{model}/schedule.json").read_text())["weights"]
            if actual != expected:
                raise ValueError("Schedule reconstruction mismatch")
            blockers = terminal_blockers(expected, name, checked_manifest(PREPARED).get("terminal_boundaries", {}))
            if blockers:
                for bps in (5, 10):
                    status = json.loads((RESULTS / f"{name}/{model}/slippage_{bps}bps/_blocked.json").read_text())
                    if status["blockers"] != blockers or status["status"] != "blocked_unverified_settlement":
                        raise ValueError("Blocked-case evidence mismatch")
                continue
            for bps in (5, 10):
                folder = RESULTS / f"{name}/{model}/slippage_{bps}bps"
                result = verify_case(folder, [name, model, bps, False], contract_hash)
                daily = pd.read_csv(folder / "daily.csv")
                data = validate_daily(daily)
                metrics, _ = performance_tables(data)
                for k, v in metrics.loc["strategy_nav"].items():
                    if pd.isna(v) and result[k] is None:
                        continue
                    if result[k] is None or abs(v-result[k]) > 1e-10:
                        raise ValueError("Reported metrics differ from saved NAV")
                if not np.allclose(daily.strategy_nav, daily.cash_usdt+daily.unrealized_usdt, rtol=0, atol=.01):
                    raise ValueError("NAV accounting mismatch")
                for symbol, column in (("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")):
                    ref = pd.read_csv(SPOT / f"{symbol}_{name}.csv")
                    if list(ref.timestamp) != list(daily.timestamp) or not np.allclose(ref.strategy_nav, daily[column], rtol=0, atol=1e-8):
                        raise ValueError("Spot benchmark mismatch")
                targets = read_ledger(folder, "targets")
                active_dates = {d for d, w in expected.items() if w}
                if active_dates-set(targets.decision_date):
                    raise ValueError("Scheduled active decision missing")
                for day, target in targets.groupby("decision_date"):
                    actual_weights = {r.instrument_id: r.weight for r in target.itertuples() if r.weight != 0}
                    if day not in expected or actual_weights != expected[day]:
                        raise ValueError("Executed weights differ from frozen schedule")
                rows.append({"window": name, "model": model, "slippage_bps": bps, **result})
        replay = verify_case(RESULTS / f"{name}/lightgbm/primary_replay", [name, "lightgbm", 5, True], contract_hash)
        original = next(r for r in rows if r["window"] == name and r["model"] == "lightgbm" and r["slippage_bps"] == 5)
        if replay["financial_sha256"] != original["financial_sha256"]:
            raise ValueError("Financial replay mismatch")
    table = pd.DataFrame(rows)
    if gates(table) != summary["evidence_gates"]:
        raise ValueError("Evidence gate mismatch")
    write(RESULTS / "verification.json", {"success": True, "verified_cases": len(rows), "verified_replays": 3,
        "experiment_data_complete": summary["data_complete"], "blocked_cases": len(summary.get("blocked_cases", [])),
        "all_planned_cases_accounted": True,
        "annual_models": 2, "strict_label_purge": True, "saved_training_order_values_verified": True,
        "continuous_year_end_cash_reset": False, "original_2024_failure_retained": True,
        "run_contract_sha256": contract_hash, "final_holdout_now_consumed": True})
    return table


def render(table):
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    primary, months_out = [], []
    for name in WINDOWS:
        folder = RESULTS / f"{name}/lightgbm/slippage_5bps"
        daily = validate_daily(pd.read_csv(folder / "daily.csv"))
        metrics = pd.read_csv(folder / "metrics.csv", index_col=0).reset_index()
        metrics["window"] = name
        primary.append(metrics)
        control = RESULTS / f"{name}/momentum60/slippage_5bps/metrics.csv"
        if control.exists():
            momentum = pd.read_csv(control, index_col=0).loc[["strategy_nav"]].reset_index()
            momentum["series"], momentum["window"] = "momentum60", name
            primary.append(momentum)
        fig, _, monthly = plot_development(daily)
        fig.suptitle(f"FINAL HOLDOUT: {name} — net of fees/funding; conditional execution")
        fig.savefig(FIGURES / f"{name}_dashboard.png", dpi=130)
        plt.close(fig)
        month = monthly.reset_index()
        month["window"] = name
        months_out.append(month)
        if name == "continuous":
            slices = []
            for year in (2025, 2026):
                a = pd.Timestamp(f"{year}-01-01", tz="UTC")
                z = pd.Timestamp("2026-01-01" if year == 2025 else "2026-10-31", tz="UTC")
                m, _ = performance_tables(daily.loc[a:z])
                m = m.reset_index()
                m["continuous_year_slice"] = year
                slices.append(m)
            pd.concat(slices).to_csv(TABLES / "continuous_year_slices.csv", index=False)
    pd.concat(primary).to_csv(TABLES / "primary_metrics.csv", index=False)
    pd.concat(months_out).to_csv(TABLES / "monthly_returns.csv", index=False)
    table.to_csv(TABLES / "verified_financial_cases.csv", index=False)
    if (RESULTS / "case_status.json").exists():
        pd.DataFrame(json.loads((RESULTS / "case_status.json").read_text())).to_csv(TABLES / "all_case_statuses.csv", index=False)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout="constrained")
    for ax, name in zip(axes, WINDOWS, strict=True):
        for model in ("lightgbm", "momentum60"):
            sub = table[(table.window == name) & (table.model == model)].sort_values("slippage_bps")
            if sub.empty:
                continue
            ax.plot(sub.slippage_bps, sub.total_return, marker="o", label=model)
        ax.set(title=name, xlabel="Extra adverse slippage (bps)", ylabel="Cumulative net return")
        ax.axhline(0, color="black", lw=.6)
        ax.legend()
    fig.savefig(FIGURES / "cost_stress.png", dpi=130)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for ax, year in zip(axes, (2025, 2026), strict=True):
        values = pd.read_csv(RESULTS / f"models/{year}/shap_importance.csv", index_col=0).iloc[:, 0]
        values.sort_values().plot.barh(ax=ax)
        ax.set(title=f"{year}: model attribution, not causal profit", xlabel="Mean absolute SHAP")
    fig.savefig(FIGURES / "shap.png", dpi=130)
    plt.close(fig)


def report():
    table = verify()
    render(table)
    prepare_notebook()
    book = nbformat.read(NOTEBOOK, as_version=4)
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    from nbclient import NotebookClient
    manager = KernelManager(kernel_name="python3", kernel_spec_manager=KernelSpecManager(
        kernel_dirs=[str(Path(sys.prefix) / "share/jupyter/kernels")]))
    NotebookClient(book, km=manager, timeout=180, allow_errors=False,
        resources={"metadata": {"path": str(ROOT)}}).execute()
    executed = ROOT / "reports/acquisition/final_holdout_results_executed.ipynb"
    nbformat.write(book, executed)
    artifacts = [*FIGURES.glob("*.png"), *TABLES.glob("*.csv"), executed]
    summary = json.loads((RESULTS / "summary.json").read_text())
    write(RESULTS / "report_complete.json", {"success": True, "experiment_data_complete": summary["data_complete"],
        "notebook_code_cells_executed": 4,
        "verification_sha256": sha(RESULTS / "verification.json"),
        "output_hashes": {str(p.relative_to(ROOT)): sha(p) for p in artifacts}})
    print(json.dumps({"success": True, "stage": "report", "verified_cases": len(table),
                      "data_complete": summary["data_complete"], "notebook_code_cells_executed": 4}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-notebook", action="store_true")
    args = parser.parse_args()
    prepare_notebook() if args.prepare_notebook else report()
