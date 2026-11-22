"""Experiment011 reports; prepare-only creates a safe English notebook scaffold."""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import nbformat
import pandas as pd
from buffer_sensitivity_worker import RESULTS, comparison_table, verify_results, write
from prepare_validation_2023 import ROOT

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

FIGURES = ROOT / "reports/figures/buffer_sensitivity"
TABLES = ROOT / "reports/tables/buffer_sensitivity"


def notebook():
    book = nbformat.v4.new_notebook(metadata={"kernelspec": {
        "display_name": "Python 3", "language": "python", "name": "python3"}})
    book.cells = [nbformat.v4.new_markdown_cell(
        "# Two-week buffer sensitivity — Experiment 011\n\n"
        "Entry rank stays 5; retention ranks are 5 (no buffer), 6, 8 and 10. "
        "All variants check membership and restore equal weights only every two weeks; "
        "actual quantities remain unchanged between decisions. Both 2022 and 2023 are "
        "development data. 2024 and final OOS remain sealed. This notebook reads saved "
        "artifacts and never launches a backtest, model fit or download."),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import Image, display\n"
            "ROOT = Path.cwd()\nif not (ROOT / 'scripts').exists():\n    ROOT = ROOT.parent\n"
            "BASE = ROOT / 'data/interim/buffer_sensitivity/v20261121_001'\n"
            "prep = json.loads((BASE / 'preparation/summary.json').read_text())\n"
            "summary_path = BASE / 'results/summary.json'\n"
            "summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}\n"
            "READY = summary.get('success', False)\n"
            "assert not prep['sealed_2024_and_final_OOS_inspected']\n"
            "display(pd.DataFrame(prep['prepared_settings']))\n"
            "print('Full results available.' if READY else 'Prepared only: run the CLI experiment to compute historical results.')"),
        nbformat.v4.new_markdown_cell("## Primary comparison\n\n"
            "Fees and funding remain identical to the prior two-week baseline. Primary extra "
            "slippage is 5bps; 10bps is mandatory stress. Membership changes differ from "
            "actual traded notional because retained positions are still resized at decision dates."),
        nbformat.v4.new_code_cell(
            "if READY:\n    display(pd.read_csv(ROOT / 'reports/tables/buffer_sensitivity/primary_metrics.csv'))\n"
            "    display(Image(filename=str(ROOT / 'reports/figures/buffer_sensitivity/rank_sensitivity.png')))\n"
            "else:\n    print('No candidate historical performance has been computed yet.')"),
        nbformat.v4.new_markdown_cell("## Equity, cost stress and concentration\n\n"
            "A wider buffer may retain weakening assets. Look for consistency across years and "
            "nearby tested ranks, not the single highest return. Best-month exclusion is descriptive, "
            "not a tradable timing rule. All 16 cases are retained."),
        nbformat.v4.new_code_cell(
            "if READY:\n    display(Image(filename=str(ROOT / 'reports/figures/buffer_sensitivity/equity.png')))\n"
            "    display(Image(filename=str(ROOT / 'reports/figures/buffer_sensitivity/cost_stress.png')))\n"
            "    display(pd.read_csv(ROOT / 'reports/tables/buffer_sensitivity/monthly_returns.csv'))"),
        nbformat.v4.new_markdown_cell("## Prespecified gates and verification\n\n"
            "A candidate must improve Sharpe, avoid worse MDD, reduce notional and remain profitable "
            "outside the best month in both primary years, and remain positive at 10bps. "
            "There is no automatic threshold replacement or opening of 2024. Models and scores "
            "are unchanged, so original SHAP is reused. Conditional universe, fractional lot, "
            "hourly VWAP and funding-mark assumptions still limit interpretation."),
        nbformat.v4.new_code_cell(
            "if READY:\n    display(pd.read_csv(ROOT / 'reports/tables/buffer_sensitivity/paired_comparisons.csv'))\n"
            "    display(pd.read_csv(BASE / 'results/all_runs.csv'))\n"
            "    display(summary)\n"
            "    display(json.loads((BASE / 'results/verification.json').read_text()))\n"
            "else:\n    print('After completion: python scripts/run_buffer_sensitivity.py --stage summary')")]
    for i, cell in enumerate(book.cells):
        cell["id"] = f"buffer-sensitivity-{i}"
    nbformat.validate(book)
    nbformat.write(book, ROOT / "notebooks/two_week_buffer_sensitivity.ipynb")
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    from nbclient import NotebookClient
    manager = KernelManager(kernel_name="python3", kernel_spec_manager=KernelSpecManager(
        kernel_dirs=[str(Path(sys.prefix) / "share/jupyter/kernels")]))
    NotebookClient(book, km=manager, timeout=180, allow_errors=False,
                   resources={"metadata": {"path": str(ROOT)}}).execute()
    nbformat.write(book, ROOT / "reports/acquisition/two_week_buffer_sensitivity_executed.ipynb")


def report(prepare_only=False):
    if prepare_only:
        notebook()
        print(json.dumps({"success": True, "stage": "notebook_prepared", "historical_runs_executed": False,
                          "code_cells_executed": 4}), flush=True)
        return
    summary = json.loads((RESULTS / "summary.json").read_text())
    if not summary["success"] or summary["completed_cases"] != 16 or summary["verified_replays"] != 2:
        raise ValueError("Full experiment is incomplete; run/resume --stage all first")
    table = verify_results()
    if len(table) != 16 or table.duplicated(["year", "retention_rank", "slippage_bps"]).any():
        raise ValueError("Case grid mismatch")
    saved = pd.read_csv(RESULTS / "all_runs.csv")
    pd.testing.assert_frame_equal(saved, table, check_dtype=False, rtol=1e-12, atol=1e-10)
    pairs = comparison_table(table)
    supported = [rank for rank in (6, 8, 10) if pairs[pairs.retention_rank == rank][["primary_gate", "stress_positive"]].to_numpy().all()]
    if summary["supported_retention_ranks"] != supported:
        raise ValueError("Reported gates differ from independently recomputed comparisons")
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    table.to_csv(TABLES / "all_registered_runs.csv", index=False)
    primary = table[table.slippage_bps == 5]
    primary.to_csv(TABLES / "primary_metrics.csv", index=False)
    pairs.to_csv(TABLES / "paired_comparisons.csv", index=False)
    monthly = []
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for ax, year in zip(axes, (2022, 2023), strict=True):
        for rank in (5, 6, 8, 10):
            folder = RESULTS / f"{year}/retain_{rank:02d}/slippage_5bps"
            daily = pd.read_csv(folder / "daily.csv")
            ax.plot(pd.to_datetime(daily.timestamp), daily.strategy_nav/100000, label=f"Retain {rank}")
            values = pd.read_csv(folder / "monthly_returns.csv").iloc[:, :2]
            values.columns = ["month", "return"]
            values["year"], values["retention_rank"] = year, rank
            monthly.append(values)
        ax.set(title=f"{year}: same two-week phase", ylabel="Net equity / initial cash")
        ax.axhline(1, color="black", lw=.6)
        ax.legend()
        ax.tick_params(axis="x", rotation=30)
    fig.savefig(FIGURES / "equity.png", dpi=150)
    plt.close(fig)
    pd.concat(monthly, ignore_index=True).to_csv(TABLES / "monthly_returns.csv", index=False)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    for year in (2022, 2023):
        values = primary[primary.year == year].sort_values("retention_rank")
        ratios = values.traded_notional / values[values.retention_rank == 5].traded_notional.iloc[0]
        for ax, y in zip(axes.flat, (values.total_return, values.Sharpe_rf0, values.MDD, ratios), strict=True):
            ax.plot(values.retention_rank, y, marker="o", label=str(year))
            ax.set_xticks([5, 6, 8, 10])
            ax.set_xlabel("Retention rank (entry stays 5)")
            ax.legend()
            ax.grid(alpha=.2)
    for ax, title in zip(axes.flat, ("Net return, primary5bps", "Sharpe (rf=0)", "MDD (closer to zero is better)", "Notional / no-buffer control"), strict=True):
        ax.set_title(title)
    axes[0, 0].yaxis.set_major_formatter(PercentFormatter(1))
    axes[1, 0].yaxis.set_major_formatter(PercentFormatter(1))
    fig.savefig(FIGURES / "rank_sensitivity.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for ax, year in zip(axes, (2022, 2023), strict=True):
        for bps in (5, 10):
            sample = table[(table.year == year) & (table.slippage_bps == bps)].sort_values("retention_rank")
            ax.plot(sample.retention_rank, sample.total_return, marker="o", label=f"{bps}bps")
        ax.set(title=str(year), xlabel="Retention rank", ylabel="Net return", xticks=[5, 6, 8, 10])
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.legend()
    fig.savefig(FIGURES / "cost_stress.png", dpi=150)
    plt.close(fig)
    write(RESULTS / "verification.json", {"success": True, "verified_cases": 16, "verified_replays": 2,
          "original_models_unchanged": True, "new_model_fits": 0, "sealed_2024_and_final_OOS_inspected": False})
    notebook()
    print(json.dumps({"success": True, "verified_cases": 16, "notebook_code_cells_executed": 4,
                      "supported_retention_ranks": supported}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    report(parser.parse_args().prepare_only)
