"""Verify Experiment010 and render all prespecified comparisons, without new fits."""

import argparse
import json
import sys
from pathlib import Path

import lightgbm as lgb
import matplotlib
import nbformat
import numpy as np
import pandas as pd
from audit_development_continuity import sha
from prepare_validation_2023 import FEATURES, PREPARED, ROOT, write
from run_first_development import PARAMS
from run_strategy_adjustments import BASE, fold_sources
from strategy_adjustment_rules import CONFIGS, portfolio_schedule, training_rows

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, StrMethodFormatter

FIGURES = ROOT / "reports/figures/strategy_adjustments"
TABLES = ROOT / "reports/tables/strategy_adjustments"


def verify(output):
    summary = json.loads((output / "summary.json").read_text())
    contract = json.loads((output / "run_contract.json").read_text())
    if not summary["success"] or summary["registered_cases"] != 32 or len(summary["replay_hashes"]) != 2:
        raise ValueError("Incomplete experiment")
    cases = pd.read_csv(output / "all_runs.csv")
    actual_keys = set(zip(cases.year, cases.config, cases.slippage_bps, strict=True))
    expected_keys = {(year, config, bps) for year in (2022, 2023) for config in CONFIGS for bps in (5, 10)}
    if len(cases) != 32 or actual_keys != expected_keys:
        raise ValueError("Missing or duplicated registered case")
    if any(sha(Path(path)) != digest for path, digest in contract["sources"].items()):
        raise ValueError("Original source/model cache changed")
    prepared = json.loads((PREPARED / "manifest.json").read_text())
    if any(sha(PREPARED / name) != digest for name, digest in prepared["output_hashes"].items()):
        raise ValueError("Prepared cache changed")
    frame = pd.read_parquet(PREPARED / "features.parquet").sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    max_shap = 0.
    verified = 0
    for year in (2022, 2023):
        source, _ = fold_sources(year)
        original = pd.read_parquet(source / "model/validation_predictions.parquet")
        cutoff = int(pd.Timestamp(f"{year}-01-01", tz="UTC").timestamp()*1000)
        for config, settings in CONFIGS.items():
            sample = original.copy()
            if settings["drop"]:
                folder = output / "models" / str(year) / config
                metadata = json.loads((folder / "metadata.json").read_text())
                train = pd.read_parquet(folder / "training_samples.parquet")
                pd.testing.assert_frame_equal(train, training_rows(frame, cutoff), check_exact=True)
                columns = [f for f in FEATURES if f not in settings["drop"]]
                if metadata["parameters"] != PARAMS or metadata["features"] != columns or metadata["latest_label_available_ms"] >= cutoff:
                    raise ValueError("Ablation definition/training boundary changed")
                sample = pd.read_parquet(folder / "validation_predictions.parquet")
                pd.testing.assert_frame_equal(sample.drop(columns="score").reset_index(drop=True),
                                              original.drop(columns="score").reset_index(drop=True), check_dtype=False, check_exact=True)
                booster = lgb.Booster(model_file=str(folder / "lightgbm.txt"))
                if sha(folder / "lightgbm.txt") != metadata["model_sha256"] or not np.allclose(
                        booster.predict(sample[columns]), sample.score, rtol=0, atol=1e-12):
                    raise ValueError("Ablation model prediction mismatch")
                shap = pd.read_csv(folder / "shap_values.csv")
                error = float((shap.filter(regex="^shap_").sum(axis=1)+shap.expected_value-shap.score).abs().max())
                if error > 1e-6 or len(shap) != len(sample):
                    raise ValueError("Ablation SHAP check failed")
                max_shap = max(max_shap, error)
            elif config == "E_funding_only":
                sample["score"] = -sample.funding7
            expected, _ = portfolio_schedule(sample, year, weeks=settings["weeks"], buffer=settings["buffer"])
            saved = json.loads((output / str(year) / config / "schedule.json").read_text())["weights"]
            if expected != saved:
                raise ValueError("Schedule differs from registered rules")
            for bps in (5, 10):
                folder = output / str(year) / config / f"slippage_{bps}bps"
                engine = json.loads((folder / "engine_summary.json").read_text())
                if config == "A_weekly":
                    ref = json.loads((source / f"lightgbm_validation/slippage_{bps}bps/engine_summary.json").read_text())
                    if ref != engine:
                        raise ValueError("Cached A financial identity mismatch")
                daily = pd.read_csv(folder / "daily.csv")
                fills = pd.read_csv(folder / "fills.csv")
                funding = pd.read_csv(folder / "funding.csv")
                if (pd.to_datetime(daily.timestamp, utc=True).dt.year != year).any() or len(daily) != 365:
                    raise ValueError("Scope/grid mismatch")
                if not np.isfinite(daily.strategy_nav).all() or (daily.strategy_nav <= 0).any() or not np.allclose(
                        daily.strategy_nav, daily.cash_usdt+daily.unrealized_usdt, rtol=0, atol=.01):
                    raise ValueError("Invalid NAV")
                for col, amount in (("commissions_usdt", fills.commission_usdt.sum()),
                                    ("funding_cashflow_usdt", funding.cashflow_usdt.sum()),
                                    ("traded_notional_usdt", fills.notional_usdt.sum())):
                    if abs(daily[col].sum()-amount) > .001:
                        raise ValueError("Ledger mismatch")
                days = pd.to_datetime(fills.timestamp_ns, unit="ns", utc=True).dt.strftime("%Y-%m-%d")
                if not set(days) <= set(expected) | {f"{year}-12-30"}:
                    raise ValueError("Trade occurred on unscheduled date")
                targets = pd.read_csv(folder / "targets.csv")
                for day, group in targets.groupby("decision_date"):
                    actual = dict(zip(group[group.weight != 0].instrument_id, group[group.weight != 0].weight, strict=True))
                    if actual != expected.get(day):
                        raise ValueError("Actual target weights differ from schedule")
                if abs(engine["ledger_error_usdt"]) > .01:
                    raise ValueError("Final ledger mismatch")
                verified += 1
        replay = json.loads((output / str(year) / "B_buffer/primary_replay/engine_summary.json").read_text())
        primary = json.loads((output / str(year) / "B_buffer/slippage_5bps/engine_summary.json").read_text())
        if replay["financial_sha256"] != summary["replay_hashes"][str(year)] or replay != primary:
            raise ValueError("Buffer replay mismatch")
    report = {"success": True, "verified_cases": verified, "verified_ablation_models": 6,
              "SHAP_additivity_max_error": max_shap, "verified_buffer_replays": 2,
              "sealed_2024_and_final_OOS_inspected": False, "source_models_unchanged": True}
    write(output / "independent_verification.json", report)
    return summary


def render(output):
    summary = verify(output)
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    runs = pd.read_csv(output / "all_runs.csv")
    pairs = pd.read_csv(output / "paired_comparisons.csv")
    runs.to_csv(TABLES / "all_registered_runs.csv", index=False)
    pairs.to_csv(TABLES / "paired_comparisons.csv", index=False)
    cols = ["year", "config", "total_return", "Sharpe_rf0", "MDD", "traded_notional", "fees", "funding",
            "best_month", "best_month_return", "other_months_compounded_return", "concentrated_positive_year"]
    primary = runs[runs.slippage_bps == 5][cols]
    primary.to_csv(TABLES / "primary_metrics.csv", index=False)
    monthly = []
    for stage, configs in (("execution", list(CONFIGS)[:4]), ("features", ["A_weekly", *list(CONFIGS)[4:]])):
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), layout="constrained")
        for ax, year in zip(axes, (2022, 2023), strict=True):
            for config in configs:
                folder = output / str(year) / config / "slippage_5bps"
                daily = pd.read_csv(folder / "daily.csv")
                ax.plot(pd.to_datetime(daily.timestamp), daily.strategy_nav/100000, label=config)
                if stage == "features" or config != "A_weekly":
                    months = pd.read_csv(folder / "monthly_returns.csv").iloc[:, :2]
                    months.columns = ["month", "return"]
                    months["config"], months["year"] = config, year
                    monthly.append(months)
            ax.set(title=f"{year}: {stage} comparisons (5bps)", ylabel="Net equity / initial cash")
            ax.axhline(1, color="black", lw=.6)
            ax.legend(fontsize=8)
            ax.tick_params(axis="x", rotation=30)
        fig.savefig(FIGURES / f"{stage}_equity.png", dpi=150)
        plt.close(fig)
    pd.concat(monthly, ignore_index=True).to_csv(TABLES / "monthly_returns.csv", index=False)
    shap_rows = []
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), layout="constrained")
    for row, year in enumerate((2022, 2023)):
        for col, config in enumerate(("F_no_momentum", "G_no_funding", "H_no_imbalance")):
            importance = pd.read_csv(output / "models" / str(year) / config / "shap_importance.csv", index_col=0).iloc[:, 0]
            axes[row, col].barh(importance.index, importance.to_numpy())
            axes[row, col].set(title=f"{year}: {config}", xlabel="Mean absolute SHAP")
            axes[row, col].xaxis.set_major_locator(MaxNLocator(nbins=4))
            axes[row, col].xaxis.set_major_formatter(StrMethodFormatter("{x:.3f}"))
            shap_rows.extend({"year": year, "config": config, "feature": name, "mean_absolute_SHAP": float(value)}
                             for name, value in importance.items())
    fig.suptitle("Ablation models: prediction attribution, not causal PnL")
    fig.savefig(FIGURES / "ablation_shap.png", dpi=150)
    plt.close(fig)
    pd.DataFrame(shap_rows).to_csv(TABLES / "ablation_shap_importance.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), layout="constrained")
    positions = np.arange(len(CONFIGS))
    for i, year in enumerate((2022, 2023)):
        values = primary[primary.year == year].set_index("config").reindex(CONFIGS)
        axes[0].bar(positions+(i-.5)*.36, values.Sharpe_rf0, width=.36, label=str(year))
        axes[1].bar(positions+(i-.5)*.36, values.traded_notional/1e6, width=.36, label=str(year))
    for ax, title in zip(axes, ("Sharpe (rf=0), primary5bps", "Traded notional (million USDT)"), strict=True):
        ax.set_xticks(positions, list(CONFIGS), rotation=50, ha="right")
        ax.set_title(title)
        ax.axhline(0, color="black", lw=.6)
        ax.legend()
    fig.savefig(FIGURES / "sharpe_and_turnover.png", dpi=150)
    plt.close(fig)
    make_notebook(output)
    print(json.dumps({"success": True, "cases": len(runs), "supported_execution_candidates": summary["supported_execution_candidates"]}))


def make_notebook(output):
    book = nbformat.v4.new_notebook(metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
    book.cells = [nbformat.v4.new_markdown_cell(
        "# Bounded strategy adjustments — Experiment 010\n\nBoth 2022 and 2023 are development data after inspection. "
        "2024 and final OOS remain sealed. Eight prespecified configurations, no Cartesian search. "
        "A weekly; B rank buffer 5/8; C two-week; D four-week; E negative-funding ranking; "
        "F no momentum; G no funding feature; H no imbalance. Funding cashflows remain in all cases."),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import Image, display\n"
            "ROOT = Path.cwd()\nif not (ROOT / 'scripts').exists():\n    ROOT = ROOT.parent\n"
            f"OUTPUT = ROOT / {str(output.relative_to(ROOT)).replace(chr(92), '/')!r}\n"
            "summary = json.loads((OUTPUT / 'summary.json').read_text())\n"
            "assert summary['success'] and not summary['sealed_2024_and_final_OOS_inspected']\n"
            "display(pd.read_csv(ROOT / 'reports/tables/strategy_adjustments/primary_metrics.csv'))"),
        nbformat.v4.new_markdown_cell("## Execution changes\n\nB/C/D reuse the exact original predictions. "
            "Buffer retains eligible names through rank 8 and still resizes weekly. "
            "Slower variants keep actual quantities between their fixed-phase decisions. "
            "Labels remain seven-day forecasts; no holding-period label change."),
        nbformat.v4.new_code_cell("display(Image(filename=str(ROOT / 'reports/figures/strategy_adjustments/execution_equity.png')))\n"
            "display(Image(filename=str(ROOT / 'reports/figures/strategy_adjustments/sharpe_and_turnover.png')))"),
        nbformat.v4.new_markdown_cell("## Feature diagnostics\n\nAblations refit with the same chronological training rows/labels "
            "and parameters, dropping only specified inputs. SHAP describes predictions, not causal PnL. "
            "Funding-only direction is fixed a priori, not selected from two signs."),
        nbformat.v4.new_code_cell("display(Image(filename=str(ROOT / 'reports/figures/strategy_adjustments/features_equity.png')))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/strategy_adjustments/paired_comparisons.csv'))\n"
            "display(Image(filename=str(ROOT / 'reports/figures/strategy_adjustments/ablation_shap.png')))"),
        nbformat.v4.new_markdown_cell("## All cases, concentration and verification\n\nDo not treat the best development result "
            "as independent validation. Compare both years, costs, drawdown and concentration. "
            "Original conditional universe/execution limitations still apply."),
        nbformat.v4.new_code_cell("display(pd.read_csv(OUTPUT / 'all_runs.csv'))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/strategy_adjustments/monthly_returns.csv'))\n"
            "display(summary)\n"
            "display(json.loads((OUTPUT / 'independent_verification.json').read_text()))")]
    path = ROOT / "notebooks/strategy_adjustments_results.ipynb"
    nbformat.write(book, path)
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    from nbclient import NotebookClient
    manager = KernelManager(kernel_name="python3", kernel_spec_manager=KernelSpecManager(
        kernel_dirs=[str(Path(sys.prefix) / "share/jupyter/kernels")]))
    NotebookClient(book, km=manager, timeout=180, allow_errors=False,
                   resources={"metadata": {"path": str(ROOT)}}).execute()
    nbformat.write(book, ROOT / "reports/acquisition/strategy_adjustments_results_executed.ipynb")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=BASE / "results")
    render(parser.parse_args().results)
