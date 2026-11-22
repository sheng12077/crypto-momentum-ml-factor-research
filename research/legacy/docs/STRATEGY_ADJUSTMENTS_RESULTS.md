# Bounded strategy adjustments: two-week execution is the supported candidate

## Material Passport

- Experiment 010, preregistration 09b0acc before implementation/execution.
- Verification status: VERIFIED; actual Nautilus simulations, independent ledger/
  model/schedule checks, two financial replays, SHAP and executed English notebook.
- Both 2022 and 2023 were already inspected and are development data here.
  2024 and final OOS remain sealed; no deployment or untouched-OOS claim.
- Fixed conditional 37-asset cohort and original execution/data limitations apply.

## Supported conclusion

C, rebalancing every two weeks, is the only execution variant passing all four
registered conditions in both years at 5bps: positive net return, higher Sharpe,
no worse MDD, and lower traded notional versus A. The other feature experiments
give reasons to retain the existing three groups rather than add new signals now.

All primary results include the same taker fees, funding and 5bps extra adverse
slippage. Each year starts from fresh 100,000USDT cash on the matched calendar.

| Configuration | 2022 return | Sharpe | MDD | 2023 return | Sharpe | MDD |
|---|---:|---:|---:|---:|---:|---:|
| A: weekly, original | +22.24% | 1.03 | -14.09% | +4.14% | 0.30 | -18.44% |
| B: weekly buffer 5/8 | +26.53% | 1.16 | -15.37% | +4.76% | 0.33 | -19.83% |
| C: every two weeks | +44.17% | 1.86 | -13.56% | +18.06% | 0.95 | -10.51% |
| D: every four weeks | +30.05% | 1.30 | -16.04% | +15.93% | 0.86 | -13.59% |
| E: negative-funding ranking | +52.23% | 1.96 | -18.33% | -17.26% | -0.79 | -22.99% |
| F: remove momentum | +25.83% | 1.36 | -15.15% | -13.84% | -0.66 | -24.90% |
| G: remove funding feature | +4.61% | 0.31 | -15.63% | +2.55% | 0.23 | -19.85% |
| H: remove imbalance | +19.52% | 0.89 | -13.15% | +0.18% | 0.12 | -22.21% |

## Execution and concentration

| Two-week C diagnostic | 2022 | 2023 |
|---|---:|---:|
| Traded notional relative to A | 58.50% | 63.03% |
| Net return at 10bps stress | +41.53% | +15.72% |
| Sharpe at 10bps stress | 1.77 | 0.84 |
| Other eleven months compounded return | +19.74% | +8.11% |
| Best month share of annual cash profit | 51.26% | 55.11% |

The best month remains June in both years. Unlike A, C is profitable even in the
descriptive product of other monthly returns. Concentration is reduced, not
eliminated: a single month still contributes roughly half of annual cash profit.
Excluding a month is not a tradable strategy and is not a seasonal timing rule.

Cost savings help, but do not explain all improvement. C commissions fall from
4048.72 to 2368.47USDT in 2022 and 3727.81 to 2349.63USDT in 2023; the changes in
annual net profit are much larger. Held positions and their marked price/funding
paths also change. This experiment does not identify a causal mechanism for the
holding-period benefit or prove that two weeks is universally optimal.

B cuts traded notional by about 18% and modestly raises Sharpe, but worsens MDD in
both years. D lowers turnover further and improves Sharpe, but fails the MDD gate
in 2022. These are tradeoffs, not evidence that buffer or four-week holding is
always ineffective. No additional buffer/cadence combinations were searched.

Cadence uses one preregistered phase anchored to the year's first Monday. Alternate
start phases are untested. Only rebalance frequency changes; the seven-day forecast
label is unchanged. Between decisions actual quantities remain fixed, so weights
can drift. Buffer still resizes retained positions weekly and does not eliminate
resizing costs. These qualifications matter when interpreting lower turnover.

## Feature diagnostics

- Removing funding lowers Sharpe in both years. Funding-only ranking, however,
  wins strongly in 2022 and loses in 2023; simple carry ranking is not a consistent
  replacement for the combined model in this comparison.
- Removing imbalance also lowers Sharpe in both years. This supports retaining
  its predictive input under the tested specification, not a causal alpha claim.
- Removing momentum helps 2022 but harms 2023 substantially. There is no consistent
  two-year case for deleting the momentum group.
- Each ablation refits on the identical chronological training rows/labels with
  unchanged parameters, excluding only its stated input columns. Removing the
  funding feature never removes actual funding cashflows from the simulator.
- All six ablation models have full-validation SHAP with additivity verification.
  SHAP measures prediction attribution, not realized factor PnL or causal importance.

## Verification and artifacts

Completed all 32 cases: four cached A references, 28 new actual Nautilus simulations,
plus two deterministic B primary replays. Six new ablation fits; no new feeds or
downloads. All unfavorable results are retained. Models, source caches and original
predictions remain unchanged. Original training boundaries and label purges apply;
no 2023 label computation, no 2024/final-OOS input or performance inspection.

Independent verification checks all 32 case keys, source hashes, retained A financial
identities, actual schedules/weights/trade dates, finite positive marked NAV,
cash+unrealized equity, fee/funding/notional ledgers and final engine reconciliation.
Six ablation model predictions/training sets and SHAP are verified; maximum SHAP
residual 1.25e-16. Two replay financial hashes match their primary runs.

Tests: isolated engine runtime 12 focused tests passed, including actual skipped-week
quantity holding, rank retention/exit/reset/ties, phase, purge and funding accounting.
Native regression 283passed/5optional-dependency skips. Ruff passed. Figures visually
checked, English notebook four code cells executed without fitting or trading.

- notebooks/strategy_adjustments_results.ipynb (English, clean saved source)
- reports/acquisition/strategy_adjustments_results_executed.ipynb (executed copy)
- data/interim/strategy_adjustments/v20261121_001/results/{summary,run_contract,independent_verification}.json
- results/{all_runs,paired_comparisons}.csv and per-year/config/slippage ledgers
- reports/tables/strategy_adjustments/{primary_metrics,monthly_returns,all_registered_runs,paired_comparisons,ablation_shap_importance}.csv
- reports/figures/strategy_adjustments/{execution_equity,features_equity,sharpe_and_turnover,ablation_shap}.png
- reports/acquisition/strategy_adjustments_{tests,run,report,regression}_20261121.log

From the strategy root in the existing isolated Python3.13 runtime:

```text
python -m pytest tests/test_strategy_adjustments.py tests/test_first_development.py tests/test_validation_2023.py -q
python scripts/run_strategy_adjustments.py
python scripts/report_strategy_adjustments.py
```

Runner version contracts prevent reusing output paths with changed rules/code/input.
`--output`/report `--results` allow explicit new versions for documented engineering
reruns; they do not authorize changing the registered strategy or selecting outcomes.

## Next boundary

C is a promising development candidate, selected after multiple comparisons on two
inspected years. It is not an independently validated trading edge. Do not add new
signals, combine variants or automatically open 2024. Discuss whether to freeze C
for a new-window test, with the same phase/rules/costs, or preregister a separate
robustness diagnostic. Universe/identity, fractional lots, historical exchange
filters/liquidation and hourly VWAP/funding proxy limitations remain unchanged.
