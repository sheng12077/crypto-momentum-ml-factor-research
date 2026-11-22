# Experiment 012: weighting matters, but no consistent replacement for equal weights

## Material Passport

- Registered1406e9b before implementation/performance, experiment012.
- Verification status: VERIFIED:12cases,1560risk/weight audit rows, two financial
  replays and executed English notebook. No new model fit or source download.
-2022/2023are inspected development years. User explicitly keeps later windows
  sealed until research is ready. No2024/final-OOS values/performance were opened.
- Conditional37-asset identity/universe and original execution caveats remain.

## Result

Weighting changes results materially. Neither IV60nor RANKpasses the prespecified
both-year improvement gates. Keep equal weights as the current development baseline;
this is not evidence that equal weights are universally optimal.

Primary5bps extra slippage, same fees/funding and100,000USDT initial cash per year:

| Allocation | 2022 return | Sharpe | MDD | 2023 return | Sharpe | MDD |
|---|---:|---:|---:|---:|---:|---:|
| EQ, equal weights | +44.17% | 1.86 | -13.56% | +18.06% | 0.95 | -10.51% |
| IV60, capped inverse volatility | +31.07% | 1.46 | -13.52% | +24.96% | 1.22 | -9.12% |
| RANK, mild rank tilt | +40.81% | 1.75 | -12.45% | +11.71% | 0.67 | -11.88% |

IV60passes the primary gate in2023but not2022, where it sacrifices13.10percentage
points of return and lowers Sharpe. This is a cross-year tradeoff, not a uniformly
bad allocation. A different risk/return objective could favor another tradeoff,
but the registered criterion must not be revised after seeing the result.

RANKlowers Sharpe in both years. The tested mild tilt does not support betting
more on the highest-ranked selected name. This does not invalidate selection/ranking
generally, nor establish that every possible tilt is inferior. No ratio search followed.

## Costs, risk and concentration

| Allocation | 2022 return at10bps | 2023 return at10bps |
|---|---:|---:|
| EQ | +41.53% | +15.72% |
| IV60 | +28.65% | +22.44% |
| RANK | +38.22% | +9.49% |

At5bps, other-best-months compounded returns for EQ/IV60/RANK are respectively
+19.74/+11.04/+16.67% in2022 and+8.11/+15.13/+1.02% in2023. RANK2023at10bps
becomes concentration-dependent: other months compound to-0.77%.

Inverse individual-asset volatility does not guarantee lower portfolio volatility.
Realized annualized volatility is20.91/19.86/20.82% for EQ/IV60/RANK in2022 and
19.62/19.90/19.42% in2023. Correlations, changing holdings and price paths matter;
we did not estimate a full covariance matrix or implement full risk parity.

No new leverage: every scheduled portfolio targets long50%,short50%,gross100%.
Max per-name weights EQ10%,RANK12.5%,IV60at most15%. IVcap is active on5and15
position-decisions in2022/2023. Daily sigma floor0.005is inactive on all selected
observations. Minimum effective names per IVside4.34/4.24 versus5for EQ; this is
allocation concentration, not the portfolio's number of independent risk sources.

## Fixed construction and availability

- Exact same selected names, models, scores, two-week first-Monday phase, no buffer,
  seven-day forecast label, execution and year-end calendar as Experiment010C.
- Same dates and5long/5short names across all three allocations. Held quantities
  remain unchanged between scheduled decisions; retained names resize on decisions.
- IV60uses61consecutive daily closing prices/60simple returns, sample ddof1;
  a23UTChour close is available at next00UTC. All observations are known by
  Monday00UTCfeature cutoff. No forward fill, name reselection or risk input failures.
- Floor daily sigma0.005, inverse-sigma proportional allocation separately per side,
  cap absweight15%NAV, redistribute among uncapped names proportionally.
- RANKuses fixed25/22.5/20/17.5/15%of each side's budget: NAVweights
  12.5/11.25/10/8.75/7.5%. Strongest selected long/weakest selected short gets most.
  Raw model scores are not treated as calibrated return magnitudes/probabilities.
- All original SHAP is reused because models/predictions are unchanged; none of
  these SHAP values is claimed to attribute realized allocation PnL.

## Verification and reproduction

12cases complete: four cached EQ financial controls, eight new actual Nautilus
histories, plus IV60/5bps replay in each year. New model fits0. Prepared audit
1560rows before candidate PnL; identical membership and all risk inputs verified.

Independent verification reconstructs weights from scoped risk closes and cached
scores, checks61price availability/caps/budgets, input/code/model hashes, actual
target weights/fill dates, marked NAV/cash/funding/fee/notional ledgers and final
flat engine reconciliation. Both IVfinancial replay hashes match. Twelve reported
case keys/metrics and all1560audit rows agree with reconstructed outputs.

13focused WSL tests pass, including no-future-price perturbation, missing-day
rejection, capped redistribution, short ranking and synthetic unequal-weight
Nautilus funding/cash quantities. Four notebook code cells executed; equity and
risk/Sharpe charts visually checked. Native regression log:
reports/acquisition/weighting_regression_20261121.log:297passed/9optional-dependency
skips. Ruff passes.

The native Windows regression initially exposed32bit integer overflow in the
synthetic test's np.arange timestamp generator under older NumPy. Explicitint64
fixes that fixture; production risk timestamps already use int64. No source data,
weighting rule or historical result was changed to address this test failure.

Run in WSL using the existing compatible funding-strategy environment:

```bash
conda activate funding-strategy
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
python scripts/run_weighting_experiment.py --stage summary
```

`--stage all` verifies/reuses completed case checkpoints then rebuilds reports;
`prepare`, `run`, `report` are available separately. No automatic installs. Changed
code/input/runtime requires an explicit new `--output` version, with failures kept.

Artifacts:

- notebooks/portfolio_weighting_results.ipynb (English, clean source)
- reports/acquisition/portfolio_weighting_results_executed.ipynb (executed copy)
- data/interim/portfolio_weighting/v20261121_001/{run_contract,summary,verification}.json
- prepared/{weight_audit.csv,risk_closes.parquet,2022_EQ.json,...}
- all_runs.csv,paired_comparisons.csv; results/<year>/<scheme>/slippage_<bps>bps/
- reports/tables/portfolio_weighting/{primary_metrics,all_registered_runs,monthly_returns,weight_audit,weight_summary,paired_comparisons,original_model_shap}.csv
- reports/figures/portfolio_weighting/{equity,risk_and_sharpe,cost_stress}.png
- reports/acquisition/weighting_{prepare,run,report,regression}_20261121.log

## Research boundary

No automatic weighting replacement, extra volatility window/cap/ratio search,
new filter/factor, paper/live action or later-window disclosure. Equal weights
remain the baseline under the registered objective. All findings are development
comparisons after prior inspection; later validation is still needed when the user
decides research is ready. Historic exchange lot/margin/liquidation, hourly VWAP,
funding proxy, reference-fee and retrospective-cohort limitations are unchanged.
