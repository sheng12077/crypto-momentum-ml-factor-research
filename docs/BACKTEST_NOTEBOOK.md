# Backtest analysis notebook

Open notebooks/backtest_analysis.ipynb in JupyterLab or VS Code. This is reporting
tooling, not a new research experiment: it does not fit models, choose parameters,
execute a strategy, or inspect OOS. No new experiment thresholds are introduced.
The default notebook reads only the existing synthetic accounting summary.

Nautilus1.231.0includes trader.generate_orders_report(),generate_fills_report(),
generate_positions_report(),generate_account_report(),and analysis.create_tearsheet.
Latest documentation can describe different APIs; use the pinned runtime.
The future strategy runner must export reports before engine.dispose(). A cash
account report alone is not marked portfolio NAV when positions remain open.

## Open it from WSL

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
data/interim/runtime/analysis313/bin/python -m jupyterlab notebooks/backtest_analysis.ipynb
```

Use the local URL printed by JupyterLab. Keep its token private. The analysis
environment is separate from the frozen simulator and borrowed conda environment.
Start Jupyter using this interpreter so its default Python kernel matches.

To recreate this environment if needed:

```bash
uv venv --python 3.13 data/interim/runtime/analysis313
uv pip install --python data/interim/runtime/analysis313/bin/python \
  -r requirements/analysis-linux-py313.lock
```

Headless verification (seconds, no downloads):

```bash
data/interim/runtime/analysis313/bin/python scripts/check_analysis_notebook.py
data/interim/runtime/analysis313/bin/python -m pytest -q tests/test_backtest_analysis.py
```

Executed notebook: reports/acquisition/backtest_analysis_executed.ipynb.
PNGfigures: reports/figures/backtest_analysis/.
CSVtables/provenance: reports/tables/backtest_analysis/.
Derived outputs remain ignored. The source notebook is committed without outputs.

## Available now

Synthetic scenario table, individual fills, adverse-slippage sensitivity and
Funding sign checks. Each scenario is independent. Do not concatenate them into
an equity curve or compute Sharpe/CAGR across them.

## Historical output contract for the future runner

Leave HISTORICAL_RUN=None until a real development run exists. Then point it to
a run directory containing manifest.json and daily.csv. Example manifest schema
(this example does not claim any completed strategy run):

```json
{
  "report_type": "historical_development",
  "OOS_performance_inspected": false,
  "start_inclusive": "2021-01-01T00:00:00Z",
  "end_exclusive": "2023-01-01T00:00:00Z",
  "currency": "USDT",
  "external_cashflows": "none",
  "nav_basis": "marked_equity_net_of_fees_and_funding"
}
```

daily.csv must contain timestamp plus these numeric columns:

| Columns | Meaning |
| --- | --- |
| strategy_nav | Marked equity including unrealizedPnL, fees and funding |
| btc_nav,eth_nav | Matched-calendar, USDTbenchmark NAV with declared costs/data |
| commissions_usdt | Positive commissions incurred since previous snapshot |
| funding_cashflow_usdt | Signed actual/explicitly modeled funding cashflow |
| traded_notional_usdt | Absolute fill notional summed since previous snapshot |
| gross_exposure,net_exposure | Gross absolute/signed net notional divided by NAV |

Timestamps are unique, ascending00:00UTCdaily snapshots with no gaps. Flow columns
describe the interval ending at that snapshot; the first row is the initial
valuation with zero flows. Start all series at the same valuation instant, and
keep benchmark construction, fee assumptions, source/config hashes and run ID in
the manifest. BTC/ETHbenchmark outputs do not exist yet; no futures/spot or fee
equivalence is implied. The reader checks declared permissions before reading
NAV and rejects dates outside2021–2022; it cannot authenticate a false manifest.

Historical dashboard: normalized equity, drawdown, monthly returns, exposure,
commissions/funding and turnover. Metrics: totalreturn,CAGR,365dayvolatility,
Sharpe(riskfree0),MDD,Calmar. Undefined ratios are NaN. Partial months remain
partial; short-period annualization is diagnostic. Turnover is both-side traded
notional/priorNAV, without division by2. This is different from rank-buffer churn.

SHAP/factor ablations/cadence and buffer experiments still need trained-model and
separate-run artifacts. They are explicitly deferred in the notebook, not faked.
This notebook does not clear the historical backtest readiness gates recorded in
docs/NAUTILUS_ACCOUNTING.md.
