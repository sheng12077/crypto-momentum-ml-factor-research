"""Verify frozen2024 results and build an English read-only analysis notebook."""

import json
import shutil
import sys
from pathlib import Path

import matplotlib
import nbformat
import numpy as np
import pandas as pd
from audit_development_continuity import sha
from build_validation_2024_spot import SPOT
from prepare_validation_2024 import BASE, OLD, PREPARED, ROOT, START, write

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = BASE / "results"
FIGURES = ROOT / "reports/figures/validation_2024"
TABLES = ROOT / "reports/tables/validation_2024"


def verify():
    from prepare_validation_2024 import training_labels
    from run_validation_2024 import schedule, training_rows, verify_case

    summary = json.loads((RESULTS / "summary.json").read_text())
    if not summary["success"] or summary["registered_runs_completed"] != 4 or not summary["primary_replay_identical"]:
        raise ValueError("Incomplete2024validation")
    for folder in (PREPARED, SPOT):
        meta = json.loads((folder / ("manifest.json" if folder == PREPARED else "summary.json")).read_text())
        if any(sha(folder / name) != digest for name, digest in meta["output_hashes"].items()):
            raise ValueError("Prepared/spot source hash changed")
    features = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    original = pd.read_parquet(OLD / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    labelled = training_labels(original, pd.read_parquet(OLD / "trade.parquet"))
    pd.testing.assert_frame_equal(features[features.feature_cutoff_ms < START].reset_index(drop=True), labelled,
                                  check_exact=True, check_dtype=False)
    model = RESULTS / "model"
    saved = pd.read_parquet(model / "training_samples.parquet")
    pd.testing.assert_frame_equal(saved, training_rows(features), check_exact=True)
    predictions = pd.read_parquet(model / "validation_predictions.parquet")
    if not predictions.label.isna().all() or (saved.label_available_ms >= START).any():
        raise ValueError("Label isolation violated")
    if set(predictions.decision_date.str[:4]) != {"2024"}:
        raise ValueError("Prediction scope violated")
    from lightgbm import Booster
    from prepare_validation_2024 import FEATURES
    booster = Booster(model_file=str(model / "lightgbm.txt"))
    if not np.allclose(booster.predict(predictions[FEATURES]), predictions.score, rtol=0, atol=1e-12):
        raise ValueError("Model/prediction mismatch")
    shap = pd.read_csv(model / "shap_values.csv")
    error = float((shap.filter(regex="^shap_").sum(axis=1)+shap.expected_value-shap.score).abs().max())
    if error > 1e-6 or len(shap) != len(predictions):
        raise ValueError("SHAP additivity/coverage failed")
    for name in ("lightgbm_validation", "momentum_baseline"):
        expected_schedule = schedule(predictions, "score" if name == "lightgbm_validation" else "momentum60")
        for bps in (5, 10):
            folder = RESULTS / name / f"slippage_{bps}bps"
            verify_case(folder)
            daily = pd.read_csv(folder / "daily.csv")
            targets = pd.read_csv(folder / "targets.csv")
            if set(targets.decision_date) - set(expected_schedule):
                raise ValueError("Unexpected executed decision date")
            for day in targets.decision_date.unique():
                target = targets[targets.decision_date == day]
                actual = dict(zip(target.instrument_id, target.weight, strict=True))
                if {s: w for s, w in actual.items() if w != 0} != expected_schedule[day]:
                    raise ValueError("Executed targets differ from frozen schedule")
            for symbol, col in (("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")):
                ref = pd.read_csv(SPOT / f"{symbol}_2024.csv")
                if list(ref.timestamp) != list(daily.timestamp) or not np.allclose(ref.strategy_nav, daily[col], rtol=0, atol=1e-8):
                    raise ValueError("Benchmark mismatch")
    primary = json.loads((RESULTS / "lightgbm_validation/slippage_5bps/engine_summary.json").read_text())
    replay = json.loads((RESULTS / "lightgbm_validation/primary_replay/engine_summary.json").read_text())
    if primary["financial_sha256"] != replay["financial_sha256"]:
        raise ValueError("Replay ledger mismatch")
    report = {"success": True, "verified_cases": 4, "training_preserved_and_purged": True,
              "validation_labels_absent": True, "shap_additivity_max_error": error,
              "replay_financial_sha256": primary["financial_sha256"],
              "final_2025_2026_OOS_inspected": False}
    write(RESULTS / "independent_verification.json", report)
    return summary


def notebook():
    cells = [nbformat.v4.new_markdown_cell(
        "# Frozen 2024 validation\n\nExperiment013: train2021–2023 once, evaluate2024. "
        "Two-week long5/short5; same fixed parameters and costs. This notebook reads saved results only. "
        "2024 is authorized; final 2025-2026 OOS remains sealed. The37-asset universe and execution assumptions remain conditional."),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import Image, display\n"
            "ROOT = Path.cwd()\nif not (ROOT / 'scripts').exists():\n    ROOT = ROOT.parent\n"
            "BASE = ROOT / 'data/interim/validation_2024/v20261121_002'\n"
            "summary = json.loads((BASE / 'results/summary.json').read_text())\n"
            "assert summary['success'] and not summary['final_2025_2026_OOS_inspected']\n"
            "display(pd.read_csv(ROOT / 'reports/tables/validation_2024/primary_metrics.csv', index_col=0))"),
        nbformat.v4.new_markdown_cell("## Matched primary comparison\n\nBoth strategies start with cash in2024. "
            "Spot benchmarks use actual spot prices and fixed units. All series share the same366 NAV snapshots "
            "and365 daily returns, ending December31 at00:00UTC. Sharpe uses a zero risk-free rate."),
        nbformat.v4.new_code_cell(
            "display(Image(filename=str(ROOT / 'reports/figures/validation_2024/lightgbm_dashboard.png')))"),
        nbformat.v4.new_markdown_cell("## All cost cases and monthly concentration\n\nPrimary slippage remains5bps. "
            "Other cases are mandatory sensitivities, not alternatives to select after seeing results. "
            "Excluding the best month is descriptive and does not define a tradable strategy."),
        nbformat.v4.new_code_cell(
            "display(pd.read_csv(BASE / 'results/all_runs.csv'))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/validation_2024/monthly_returns.csv', index_col=0))\n"
            "display(pd.DataFrame(summary['concentration']).T)\n"
            "display(Image(filename=str(ROOT / 'reports/figures/validation_2024/cost_sensitivity.png')))"),
        nbformat.v4.new_markdown_cell("## Model attribution and verification\n\nSHAP describes predictions; "
            "it is not causal importance or realized factor PnL. No2024labels were fitted or used for early stopping."),
        nbformat.v4.new_code_cell(
            "display(Image(filename=str(ROOT / 'reports/figures/validation_2024/shap_importance.png')))\n"
            "display(summary['evidence_gates'])\n"
            "display(json.loads((BASE / 'results/independent_verification.json').read_text()))"),
        nbformat.v4.new_markdown_cell("## Interpretation limits\n\nOne validation year cannot establish persistent alpha. "
            "Conditional identity continuity, retrospective cohort evidence, fractional lots, hourly VWAP fills, "
            "funding mark proxies and unvalidated historical filters/liquidation remain limitations. "
            "Any strategy changes based on2024make it development data;the final 2025-2026 holdout remains sealed.")]
    book = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {
        "display_name": "Python 3", "language": "python", "name": "python3"}})
    path = ROOT / "notebooks/validation_2024_results.ipynb"
    nbformat.write(book, path)
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    from nbclient import NotebookClient
    manager = KernelManager(kernel_name="python3", kernel_spec_manager=KernelSpecManager(
        kernel_dirs=[str(Path(sys.prefix) / "share/jupyter/kernels")]))
    NotebookClient(book, km=manager, timeout=180, allow_errors=False,
                   resources={"metadata": {"path": str(ROOT)}}).execute()
    nbformat.write(book, ROOT / "reports/acquisition/validation_2024_results_executed.ipynb")


def main():
    summary = verify()
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    runs = pd.read_csv(RESULTS / "all_runs.csv")
    runs.to_csv(TABLES / "all_registered_runs.csv", index=False)
    folder = RESULTS / "lightgbm_validation/slippage_5bps"
    metrics = pd.read_csv(folder / "metrics.csv", index_col=0)
    metrics = metrics.rename(index={"strategy_nav": "LightGBM", "btc_nav": "BTC spot hold", "eth_nav": "ETH spot hold"})
    momentum = pd.read_csv(RESULTS / "momentum_baseline/slippage_5bps/metrics.csv", index_col=0)
    metrics.loc["Momentum60"] = momentum.loc["strategy_nav"]
    metrics.to_csv(TABLES / "primary_metrics.csv")
    monthly = pd.read_csv(folder / "monthly_returns.csv", index_col=0).rename(columns={"strategy_nav": "LightGBM"})
    monthly["Momentum60"] = pd.read_csv(RESULTS / "momentum_baseline/slippage_5bps/monthly_returns.csv", index_col=0).strategy_nav
    monthly.to_csv(TABLES / "monthly_returns.csv")
    shutil.copyfile(folder / "dashboard.png", FIGURES / "lightgbm_dashboard.png")
    shutil.copyfile(RESULTS / "momentum_baseline/slippage_5bps/dashboard.png", FIGURES / "momentum_dashboard.png")
    shutil.copyfile(RESULTS / "model/shap_importance.png", FIGURES / "shap_importance.png")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for name, group in runs.groupby("model"):
        axes[0].plot(group.slippage_bps, group.total_return, marker="o", label=name)
        axes[1].plot(group.slippage_bps, group.Sharpe_rf0, marker="o", label=name)
    for ax, title in zip(axes, ("Net return", "Sharpe (rf=0)"), strict=True):
        ax.set(xlabel="Extra adverse slippage per fill (bps)", title=title)
        ax.axhline(0, color="black", lw=.7)
        ax.legend()
    fig.savefig(FIGURES / "cost_sensitivity.png", dpi=150)
    plt.close(fig)
    notebook()
    print(json.dumps({"success": True, "notebook": "notebooks/validation_2024_results.ipynb",
                      "notebook_code_cells_executed": 4, "evidence_gates": summary["evidence_gates"]}))


if __name__ == "__main__":
    main()
