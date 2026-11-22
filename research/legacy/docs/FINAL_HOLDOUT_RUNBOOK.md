# Final holdout: user-run handoff

Experiment015registration4baee9d on main precedes implementation. Work branch:
exp/final-holdout-2025-2026. User will run; no final-window historical data has
been prepared, fitted, simulated or inspected by the agent during this handoff.

## Current verified state: do not ask the user to rerun

After repeated errors the user requested actual end-to-end validation. The agent
ran prepare/spot/simulation/report on real inputs in v003, reusing verified v002
data and both trained models. No repeat downloads or model fits were performed.
The report and4notebook cells executed successfully:8financial cases verified,
3MLfinancial replays identical,4planned control cases explicitly blocked for
unverified EOS terminal settlement. This is NOT full12case data completeness.

KAVA's error was an event merge bug, not a missing mark file: funding at the same
instant as execution lost its dedicated mark fields. Seven such events across
XTZ,KAVA,ONT,IOSThave valid source marks. Funding now retains its own completed
mark price/availability independently of the execution VWAP. Original failedv002
and contract remain intact; controlledv003migration copies input/model caches,
never reuses failed financial output. Original forecasts and parameters unchanged.

Open `reports/acquisition/final_holdout_results_executed.ipynb` directly. A new
backtest command is not needed to view results. `--stage summary` reports
report_verified=true but data_complete=false/success=false because4of12registered
cases cannot be certified. Missing control comparisons are null, not false or
silently passed. See docs/FINAL_HOLDOUT_EXECUTION_RESULTS.md.

## Acquisition repair: terminal archive tails

The first run stopped at EOS2025-05-21: trade bars end at the official09UTC
settlement boundary while mark archives continue. Version002 verifies cached
lifecycle announcement bytes and quarantines terminal/post-terminal hourly rows;
it retains the asset's valid pre-terminal history. OMG's terminal bucket contains
settlement prints; that bucket is excluded, not treated as a new trading episode.
Positive trading in later full-hour buckets fails for episode review.

A read-only key audit of all37assets now reports zero unresolved active trade/mark
key differences. This is availability validation, not a profitability/backtest
result.32focused synthetic/regression tests cover boundary tails and held-terminal
failure. No model fit, forecast or historical simulation was run for this repair.

Rerun the same `--stage all` command below. No manual deletion is needed. Failed
version001and its code contract remain intact; verified source caches and already
consumed request budgets are copied to version002. The model, rank selection,
fees and performance gates are unchanged. Unsupported held settlement now produces
an explicit error instead of using stale marks or an invented closing price.

## Run in WSL

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
conda activate funding-strategy
python scripts/run_final_holdout.py --stage all
python scripts/run_final_holdout.py --stage summary
```

Alternative: use `/home/sheng77/miniforge3/envs/funding-strategy/bin/python` in place
of `python`. Same environment as2024; no keys or new package installation needed.
Allow several minutes to tens of minutes depending on machine/network and source
repairs. The runner prints progress and a log under
`reports/acquisition/final_holdout_<stage>_<UTC>.log`.

## What is fixed

Original five raw inputs and LightGBM parameters, seven-day labels, two-week phase
anchored to each year's first Monday, five long/five short, equal weights, no
buffer/timing/newfilter.5bps taker,noBNB,5bps adverse-slippage primary/10bpsstress.
2025train2021--2024;2026train2021--2025. Each uses only labels strictly available
before that year's Jan1; both models are fit regardless of2025performance.

Twelve cases: ML/momentum60 x5/10bps x standalone2025,standalone2026Jan--Oct,
continuous2025--2026Oct. Three exact primary ML financial replays. Continuous
trading carries positions and NAV over year-end; it is not compounded standalone
returns. Actual BTC/ETH spot holds are matched in each window. SHAP for both models.

Prior valuation convention retained:2025lastNAVDec31 00UTC (365snapshots/364returns),
2026lastNAVOct31 00UTC (304/303),continuous669/668. Forced liquidation is previous
23UTC; final civil day's return is omitted. Continuous2025year-slice usesJan1 2026
as the ending shared snapshot, so it differs from the separately liquidated2025
case. Partial2026totalreturn is cumulative, distinct from annualized CAGR/Sharpe.

## Outputs and success

- Results: `data/interim/final_holdout/v20261122_003/results/summary.json`.
- Verification: same folder, `verification.json` and `report_complete.json`.
- Tables/figures: `reports/{tables,figures}/final_holdout/`.
- English notebook: `notebooks/final_holdout_results.ipynb` (unexecuted at handoff).
- Executed saved-results notebook: `reports/acquisition/final_holdout_results_executed.ipynb`.

Successful execution:12completed cases,3identical replays,2annual models,
report_verified=true and4notebook code cells executed. Performance gates may all
be false and the execution can still succeed. Share compact `--stage summary` JSON.
2024's failed validation remains part of the final conclusion; no automatic
paper/live promotion or tuning after disclosure.

## Resume and failures

Stages:prepare,spot,simulate,report,summary. A process lock prevents concurrent
wrapper runs. Completed case/model caches are hash-checked; failed attempt folders
and logs remain intact. Report-only failures can be resumed with `--stage report`.
Never delete a contract or choose a different cohort to get past an error.

Acquisition is official public checksummed data with persistent request budgets;
403/418/429 stops immediately. Spot2025+microsecond timestamps are normalized and
recorded. NoNov/Dec2026market values or prices afterOctoberare read. Missing held
marks/executions,unsupported lifecycle settlement or budget exhaustion fails
explicitly; the tool never fabricates a settlement or silently drops a position.
Send the traceback and final log lines if that happens.

Historical universe/lifecycle publication evidence, fractional lots, hourly VWAP
fills, recorded-funding proxies and unvalidated liquidation remain limitations.
This experiment consumes the final holdout when performance is inspected; it
cannot later validate modifications made in response to its own outcomes.
