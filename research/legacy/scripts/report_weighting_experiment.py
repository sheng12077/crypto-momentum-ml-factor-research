"""Verify Experiment012, render allocation comparisons and execute English notebook."""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import nbformat
import numpy as np
import pandas as pd
from buffer_sensitivity_worker import write
from portfolio_weighting_rules import SCHEMES, DailyRisk, build_schedule
from prepare_validation_2023 import PREPARED, ROOT
from run_strategy_adjustments import fold_sources, full_model
from run_weighting_experiment import BASE, comparisons, verify

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

TABLES = ROOT / "reports/tables/portfolio_weighting"
FIGURES = ROOT / "reports/figures/portfolio_weighting"


def verify_audit(base):
    closes = pd.read_parquet(base / "prepared/risk_closes.parquet")
    risk = DailyRisk(closes.rename(columns={"available_ms": "bar_open_ms"}).assign(bar_open_ms=closes.available_ms-3_600_000))
    features = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    rows = []
    for year in (2022, 2023):
        sample = full_model(features, year)
        for scheme in SCHEMES:
            _, audit = build_schedule(sample, year, scheme, risk)
            rows += audit
    expected = pd.DataFrame(rows)
    saved = pd.read_csv(base / "prepared/weight_audit.csv")
    pd.testing.assert_frame_equal(saved, expected, check_dtype=False, rtol=1e-12, atol=1e-12)
    if not (saved.risk_prices == 61).all():
        raise ValueError("Invalid risk sample length")
    cutoff = np.array([pd.Timestamp(day, tz="UTC").value//1_000_000 for day in saved.decision_date])
    if (saved.risk_last_available_ms.to_numpy() > cutoff).any():
        raise ValueError("Future close entered risk estimate")
    for (_, _, _), group in saved.groupby(["year", "scheme", "decision_date"]):
        if abs(group.weight.abs().sum()-1) > 1e-12 or abs(group.weight.sum()) > 1e-12 or group.weight.abs().max() > .15+1e-12:
            raise ValueError("Portfolio budget/cap failure")
    return saved


def notebook(base):
    book = nbformat.v4.new_notebook(metadata={"kernelspec": {
        "display_name": "Python 3", "language": "python", "name": "python3"}})
    book.cells = [nbformat.v4.new_markdown_cell(
        "# Portfolio weighting — Experiment 012\n\n"
        "Same selected five longs/five shorts, models and two-week no-buffer schedule. "
        "EQ: equal weights. IV60: inverse trailing 60-day return volatility, daily sigma floor "
        "0.005 and 15% NAV per-name cap. RANK: side shares 25/22.5/20/17.5/15%. "
        "All restore long 50% / short 50% only on decision dates. No leverage increase or model refit. "
        "Both 2022 and 2023 are inspected development data; 2024 and final OOS remain sealed."),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import Image, display\n"
            "ROOT = Path.cwd()\nif not (ROOT / 'scripts').exists():\n    ROOT = ROOT.parent\n"
            f"BASE = ROOT / {base.relative_to(ROOT).as_posix()!r}\n"
            "summary = json.loads((BASE / 'summary.json').read_text())\n"
            "assert summary['success'] and not summary['sealed_2024_and_final_OOS_inspected']\n"
            "display(pd.read_csv(ROOT / 'reports/tables/portfolio_weighting/primary_metrics.csv'))"),
        nbformat.v4.new_markdown_cell("## Matched equity and allocation risk\n\n"
            "The only intended difference is allocation among identical selected names. "
            "A higher raw return need not be a better risk-adjusted outcome. Inverse volatility "
            "is a simplified allocation rule, not full risk parity or beta neutrality."),
        nbformat.v4.new_code_cell(
            "display(Image(filename=str(ROOT / 'reports/figures/portfolio_weighting/equity.png')))\n"
            "display(Image(filename=str(ROOT / 'reports/figures/portfolio_weighting/risk_and_sharpe.png')))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/portfolio_weighting/weight_summary.csv'))"),
        nbformat.v4.new_markdown_cell("## Costs and monthly concentration\n\n"
            "Primary extra slippage is 5bps; 10bps is a fixed stress. Both include fees and "
            "funding. Best-month exclusion is descriptive, not a tradable rule."),
        nbformat.v4.new_code_cell(
            "display(Image(filename=str(ROOT / 'reports/figures/portfolio_weighting/cost_stress.png')))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/portfolio_weighting/monthly_returns.csv'))\n"
            "display(pd.read_csv(BASE / 'all_runs.csv'))"),
        nbformat.v4.new_markdown_cell("## Audit and interpretation\n\n"
            "Weights use only 61 consecutive completed closes available by the decision cutoff. "
            "Source models, scores and their original SHAP are unchanged; SHAP does not explain "
            "allocation PnL. No buffer, threshold or window search is performed. This notebook "
            "only reads saved results and never launches simulations or reveals sealed windows. "
            "Original conditional cohort, fractional sizing, hourly VWAP and funding-mark limits remain."),
        nbformat.v4.new_code_cell(
            "display(pd.read_csv(ROOT / 'reports/tables/portfolio_weighting/paired_comparisons.csv'))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/portfolio_weighting/original_model_shap.csv'))\n"
            "display(summary)\n"
            "display(json.loads((BASE / 'verification.json').read_text()))")]
    for i, cell in enumerate(book.cells):
        cell["id"] = f"portfolio-weighting-{i}"
    nbformat.validate(book)
    nbformat.write(book, ROOT / "notebooks/portfolio_weighting_results.ipynb")
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    from nbclient import NotebookClient
    manager = KernelManager(kernel_name="python3", kernel_spec_manager=KernelSpecManager(
        kernel_dirs=[str(Path(sys.prefix) / "share/jupyter/kernels")]))
    NotebookClient(book, km=manager, timeout=180, allow_errors=False,
                   resources={"metadata": {"path": str(ROOT)}}).execute()
    nbformat.write(book, ROOT / "reports/acquisition/portfolio_weighting_results_executed.ipynb")


def report(base):
    summary = json.loads((base / "summary.json").read_text())
    if not summary["success"] or summary["completed_cases"] != 12 or summary["verified_replays"] != 2:
        raise ValueError("Incomplete registered experiment")
    table = verify(base)
    keys = set(zip(table.year, table.scheme, table.slippage_bps, strict=True))
    if len(table) != 12 or keys != {(y, s, b) for y in (2022, 2023) for s in SCHEMES for b in (5, 10)}:
        raise ValueError("Case grid mismatch")
    pd.testing.assert_frame_equal(pd.read_csv(base / "all_runs.csv"), table, check_dtype=False, rtol=1e-12, atol=1e-10)
    audit = verify_audit(base)
    paired = comparisons(table)
    supported = [s for s in ("IV60", "RANK") if paired[paired.scheme == s][["primary_gate", "stress_positive"]].to_numpy().all()]
    if supported != summary["supported_weighting_candidates"]:
        raise ValueError("Candidate gates mismatch")
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    table.to_csv(TABLES / "all_registered_runs.csv", index=False)
    primary = table[table.slippage_bps == 5]
    primary.to_csv(TABLES / "primary_metrics.csv", index=False)
    paired.to_csv(TABLES / "paired_comparisons.csv", index=False)
    audit.to_csv(TABLES / "weight_audit.csv", index=False)
    weights = audit.assign(absweight=audit.weight.abs(), floor_active=audit.sigma_daily_raw < .005)
    weight_summary = weights.groupby(["year", "scheme"]).agg(
        max_abs_weight=("absweight", "max"), min_effective_names=("effective_names_side", "min"),
        median_effective_names=("effective_names_side", "median"), capped_positions=("cap_active", "sum"),
        floored_risk_estimates=("floor_active", "sum"))
    weight_summary.to_csv(TABLES / "weight_summary.csv")
    originals = []
    for year in (2022, 2023):
        source, _ = fold_sources(year)
        values = pd.read_csv(source / "model/shap_importance.csv", index_col=0).iloc[:, 0]
        originals += [{"year": year, "feature": name, "mean_absolute_SHAP": float(value)} for name, value in values.items()]
    pd.DataFrame(originals).to_csv(TABLES / "original_model_shap.csv", index=False)
    monthly = []
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for ax, year in zip(axes, (2022, 2023), strict=True):
        for scheme in SCHEMES:
            folder = base / f"results/{year}/{scheme}/slippage_5bps"
            daily = pd.read_csv(folder / "daily.csv")
            ax.plot(pd.to_datetime(daily.timestamp), daily.strategy_nav/100000, label=scheme)
            months = pd.read_csv(folder / "monthly_returns.csv").iloc[:, :2]
            months.columns = ["month", "return"]
            months["year"], months["scheme"] = year, scheme
            monthly.append(months)
        ax.set(title=f"{year}: same names and cadence", ylabel="Net equity / initial cash")
        ax.axhline(1, color="black", lw=.6)
        ax.legend()
        ax.tick_params(axis="x", rotation=30)
    fig.savefig(FIGURES / "equity.png", dpi=150)
    plt.close(fig)
    pd.concat(monthly, ignore_index=True).to_csv(TABLES / "monthly_returns.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    x = np.arange(3)
    for i, year in enumerate((2022, 2023)):
        values = primary[primary.year == year].set_index("scheme").reindex(SCHEMES)
        axes[0].bar(x+(i-.5)*.36, values.annualized_volatility, width=.36, label=str(year))
        axes[1].bar(x+(i-.5)*.36, values.Sharpe_rf0, width=.36, label=str(year))
    for ax, title in zip(axes, ("Realized annualized volatility", "Sharpe (rf=0)"), strict=True):
        ax.set(title=title, xticks=x, xticklabels=SCHEMES)
        ax.legend()
        ax.axhline(0, color="black", lw=.6)
    axes[0].yaxis.set_major_formatter(PercentFormatter(1))
    fig.savefig(FIGURES / "risk_and_sharpe.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for ax, year in zip(axes, (2022, 2023), strict=True):
        for scheme in SCHEMES:
            values = table[(table.year == year) & (table.scheme == scheme)].sort_values("slippage_bps")
            ax.plot(values.slippage_bps, values.total_return, marker="o", label=scheme)
        ax.set(title=str(year), xlabel="Extra adverse slippage (bps)", ylabel="Net return", xticks=[5, 10])
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.legend()
    fig.savefig(FIGURES / "cost_stress.png", dpi=150)
    plt.close(fig)
    write(base / "verification.json", {"success": True, "verified_cases": 12, "verified_replays": 2,
          "weight_audit_rows": len(audit), "past_only_risk_inputs": True, "identical_selected_membership": True,
          "new_model_fits": 0, "original_models_and_SHAP_unchanged": True,
          "sealed_2024_and_final_OOS_inspected": False})
    notebook(base)
    print(json.dumps({"success": True, "verified_cases": 12, "notebook_code_cells_executed": 4,
                      "supported_weighting_candidates": supported}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=BASE)
    report(parser.parse_args().results)
