# Continuous 2022--October 2026 reconstruction

Registration: experiments/016_continuous_2022_2026.md. Retrospective reconstruction;
not new OOS, parameter selection, or paper/live authorization. Same frozen annual
models, conditional 37-asset cohort, EQ5L/5S, two-week first-Monday phase per year,
no buffer, no Size. There can be a 7/21-day interval at year boundaries. Annual
model changes apply at the next scheduled rebalance; actual quantities/cash persist.
Original 2022--2024 training eligibility is preserved, not expanded using later
label reconstruction. Existing SHAP is checked and reported. No new fit/download.

## Run in WSL

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
conda activate funding-strategy
python scripts/run_continuous_reconstruction.py --stage all
python scripts/run_continuous_reconstruction.py --stage summary
```

Full runtime has not been measured: this runs two full-period cases and an
independent primary replay. The CLI prints each case and logs continuously.
Do not run concurrent copies or delete contracts/caches to bypass a failure.
Re-running the same command validates completed cases and resumes unfinished ones;
failed attempt directories remain available. Public APIs and credentials unused.

Stages: preflight, simulate, report, summary. Agent verifies the full cached-data
preflight and synthetic accounting/reporting before handoff; user runs historical PnL.
Preflight checks every required held daily/funding mark, sizing reference, execution
VWAP and terminal boundary, all five annual model forecasts/training samples and
116 official checksum-verified spot archives. It is not a completed backtest.
Any unresolved source/settlement blocks rather than dropping an asset or fabricating cash.
No momentum-only comparator is run: the known EOS settlement issue remains explicit.

## Products

- Log: reports/acquisition/continuous_all_<UTC timestamp>.log
- Data, source contracts, attempts, ledgers and compact summary:
  data/interim/continuous_reconstruction/v20261122_001/
- Tables: reports/tables/continuous_reconstruction/ (5/10bps metrics, daily NAV,
  monthly returns, continuous calendar-year slices and cross-year equity/cash).
- Figures: reports/figures/continuous_reconstruction/ (two dashboards, annual SHAP).
- English saved-results notebook: notebooks/continuous_reconstruction_results.ipynb.
  Open after successful CLI completion; Run All only verifies/reads saved results.
- On failure, return last_failure.json and the log tail; preserve attempt artifacts.

Success summary: success=true, report_verified=true, financial_cases=2,
verified_replays=1, new_model_fits=0, annual_cash_resets=0, fresh_OOS=false.
Economic gates may legitimately be false; successful execution does not imply profit.
Expected 1765 daily snapshots / 1764 daily returns. Last valuation Oct 31 2026 00UTC;
sole final liquidation Oct 30 23UTC. Each yearly slice includes the return ending
Jan 1 by using the preceding Dec 31 NAV as its base (2022 begins at initial NAV).
Whole-period MDD/Sharpe are recomputed from the full uninterrupted curve.

Perpetual execution: 5bps taker/noBNB, adverse slippage5/10bps; existing funding mark
proxy and pre-fill quantities. Spot benchmarks: one Jan1 2022 02UTC buy, one final
sale, 10bps taker+5bps slippage per side, fixed units. Exposure differs from long/short.
Ledger error <=0.01 USDT and independent every-fill/funding audit required, plus
exact primary financial replay. Report shows return, CAGR, volatility, Sharpe_rf0,
MDD, Calmar, fee/funding/turnover, best-month concentration and all registered gates.

Conditional universe, publication vintage, hourly execution/funding price proxies and
uncertified historical exchange lot/margin/liquidation remain material limitations.
All years have already been disclosed; no further tuning can reuse them as fresh OOS.
