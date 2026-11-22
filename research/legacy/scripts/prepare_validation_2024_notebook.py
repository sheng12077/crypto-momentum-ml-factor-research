"""Create a safe, unexecuted English notebook without opening historical results."""

from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def main():
    cells = [nbformat.v4.new_markdown_cell(
        "# Frozen 2024 validation\n\nExperiment 013. Train once on matured 2021-2023 labels; "
        "validate in 2024. Two-week long five / short five, equal weights, no buffer. "
        "Final 2025-2026 OOS remains sealed.\n\nRun `python scripts/run_frozen_2024.py --stage all` "
        "from the project root before executing this notebook. It reads saved results only."),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\nimport json\nimport pandas as pd\n"
            "from IPython.display import Image, display\nROOT = Path.cwd()\n"
            "if not (ROOT / 'scripts').exists():\n    ROOT = ROOT.parent\n"
            "BASE = ROOT / 'data/interim/validation_2024/v20261121_002'\n"
            "path = BASE / 'results/summary.json'\n"
            "assert path.exists(), 'Complete run_frozen_2024.py --stage all first.'\n"
            "summary = json.loads(path.read_text())\n"
            "assert summary['success'] and not summary['final_2025_2026_OOS_inspected']\n"
            "display(pd.read_csv(ROOT / 'reports/tables/validation_2024/primary_metrics.csv', index_col=0))"),
        nbformat.v4.new_markdown_cell(
            "## Performance and matched benchmarks\n\nAll series share 366 NAV snapshots and "
            "365 returns, ending December 31 at 00:00 UTC. BTC/ETH are fixed-unit spot holds. "
            "Net notional zero does not imply beta neutrality."),
        nbformat.v4.new_code_cell(
            "display(Image(filename=str(ROOT / 'reports/figures/validation_2024/lightgbm_dashboard.png')))"),
        nbformat.v4.new_markdown_cell(
            "## Costs and monthly concentration\n\n5 bps extra slippage is primary; 10 bps is stress. "
            "Report all cases. Removing the best month is descriptive, not a tradable rule."),
        nbformat.v4.new_code_cell(
            "display(pd.read_csv(BASE / 'results/all_runs.csv'))\n"
            "display(pd.read_csv(ROOT / 'reports/tables/validation_2024/monthly_returns.csv', index_col=0))\n"
            "display(pd.DataFrame(summary['concentration']).T)\n"
            "display(Image(filename=str(ROOT / 'reports/figures/validation_2024/cost_sensitivity.png')))"),
        nbformat.v4.new_markdown_cell(
            "## Attribution and integrity\n\nSHAP explains model predictions, not causal profits. "
            "No 2024 labels are fitted. Universe, hourly execution/funding proxies, fractional "
            "filters and unvalidated liquidation assumptions remain conditional."),
        nbformat.v4.new_code_cell(
            "display(Image(filename=str(ROOT / 'reports/figures/validation_2024/shap_importance.png')))\n"
            "display(summary['evidence_gates'])\n"
            "display(json.loads((BASE / 'results/independent_verification.json').read_text()))")]
    book = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {
        "display_name": "Python 3", "language": "python", "name": "python3"}})
    path = ROOT / "notebooks/validation_2024_results.ipynb"
    if path.exists():
        raise FileExistsError("Notebook exists; preserve existing user outputs")
    nbformat.write(book, path)
    print("Prepared unexecuted English notebook; no historical results loaded.")


if __name__ == "__main__":
    main()
