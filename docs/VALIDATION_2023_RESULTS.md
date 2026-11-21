# Frozen2023 validation: positive but weak and concentrated

## Material Passport

- Experiment009, registration57f75e5 before2023 values/performance inspection.
- Verification status: VERIFIED (actual Nautilus runs, financial replay, source/
  training/ledger checks, SHAP and executed notebook). No claim of human paper review.
- Scope: train2021–2022 once, validate2023;2024/final OOS remain sealed.
- All results conditional on the original37-asset universe/execution assumptions.

## Conclusion

The primary strategy earned4.14% with Sharpe0.30 and maximum daily drawdown18.44%.
It outperformed the matched60day momentum control, but the modest return is still
dependent on its best month. This provides limited support for the model versus
that particular control, not evidence of a robust deployable edge.

| Same2023calendar | Net return | Sharpe_rf0 | MDD |
|---|---:|---:|---:|
| LightGBM,5bps extra slippage | +4.1369% | 0.2993 | -18.4396% |
| Momentum60,5bps | -23.2525% | -1.1294 | -27.4357% |
| BTC spot fixed-unit hold | +154.5146% | 2.3425 | -20.0027% |
| ETH spot fixed-unit hold | +91.0313% | 1.6166 | -27.3313% |

Long/short target net notional0 differs economically from long-only spot hold;
these benchmark returns do not establish model alpha or equivalent market risk.
The strategy's relatively low Sharpe and drawdown comparable to BTC remain relevant.

## Concentration and costs

The best month was June+6.8867%, contributing6153.95USDT of annual4136.87USDT cash
profit (148.76%). Other eleven monthly returns compound to-2.5726%. This repeats
the concentration concern seen in2022. It does not establish June seasonality or
the same mechanism as2022: the June2023BTC spot benchmark actually rose9.94%.
Detailed2023asset/side attribution would be a separate post-hoc diagnostic.

The first half included April-6.47% and May-4.10%; June recovery and later positive
months did not produce a strong annual risk-adjusted outcome.

| Extra adverse slippage per fill | ML return | ML Sharpe | Momentum return |
|---|---:|---:|---:|
| 0bps | +8.1513% | 0.4822 | -21.8154% |
| 2bps | +6.5281% | 0.4090 | -22.3933% |
| 5bps, primary | +4.1369% | 0.2993 | -23.2525% |
| 10bps | +0.2656% | 0.1170 | -24.6643% |

The0bps case still includes5bps taker fees and funding. Costs matter, but even
without extra slippage the observed Sharpe is below0.5. Cost reduction alone is
not established as sufficient to make the strategy attractive.

PrimaryML:851fills,10880funding cashflows,7,455,625.31USDT traded notional,
3727.81USDT commissions,3166.74USDT net funding credit. Funding-feature SHAP has
the largest mean absolute contribution to predictions; this does not identify
realized causal factor PnL or justify removing other factors.

## Frozen design and verification

- Original five feature columns, LightGBM PARAMS unchanged. Expanding training
  has3804rows, latest label availability2022-12-26 03UTC, strictly before2023.
- All original corrected2021–2022features preserved exactly;2023features1924rows,
  52Mondays with37candidates each.2023labels deliberately not computed or fitted.
- Same weekly top5/bottom5, equal+/-10%NAV targets, initial100000USDT, no buffer,
  staged sizing, volatility targeting or within-year refit.
- Same01UTC sizing/02UTC preceding-hour VWAP fill and funding mark proxy.
  Same prior convention ends atDec31 00UTC after forced closeDec30 23UTC:
  365NAV rows/364daily returns, not a complete Jan1-to-nextJan1 year.
-2023canonical data needed no repairs or additional futures HTTP requests.
  Spot24monthlyZIPs/checksums:48requests,987359compressed bytes;2partial hours
  quarantined, all necessary benchmark entry/exit/valuation observations available.
- All8cases retained, final cash/closed-PnL/funding errors<=1.46e-11USDT;
  daily marked NAV, fees, funding, traded notional and spot calendars reconcile.
- Primary financial replay identical:
  `6ac3c053c45e0556135e8144d5fb51982b1593e3fc7154d6a1a7372680d1b403`.
- SHAP all1924predictions, additivity error6.94e-17. Fitted model SHA256:
  `085804c8830b40ff3453b631db0ccbe06c13aaf9eda5a49b0306b9be251bd6ab`.
- Native regression278passed/4skipped (optional engine/model packages absent).
  Isolated runtime11focused tests passed, including actual engine roundtrip,
  old default calendar,2023boundary, purge, no-future-feature use and attribution.
  Ruff passes; dashboard and SHAP chart visually checked; notebook4code cells executed.

Prespecified minimum net-return/Sharpe and incremental-control gates passed.
Concentration-dependence flag is true; the minimum gates are not statistical
significance tests or sufficient evidence of a robust trading strategy.

## Engineering notes

ExistingWindowsPython3.13.18 environment retained all66package records and versions
(Nautilus1.231.0,LightGBM4.7.0,SHAP0.54.1). A stale uv launcher/home path was
repaired using installed basePython's venv--upgrade--without-pip--copies, with
reversible backups underTEMP/momentum_development_005/launcher_backup_*.

Before simulation, tests detected Pandas3microsecond inference in the previous
attribution helper. ExplicitTimestamp.value nanoseconds fixes cross-version units;
hand-computed reversal test passes. No trading rule or old market data changed.
The engine calendar accepts end_year with the original2022default preserved.

## Artifacts and reproduction

Open notebooks/validation_2023_results.ipynb (English, saved results only).
Executed copy:reports/acquisition/validation_2023_results_executed.ipynb.
Original user-executed notebooks remain untouched.

Runtime: existing isolatedPython3.13 underTEMP/momentum_development_005/venv.
Run from the strategy root in that runtime:

```text
python scripts/prepare_validation_2023.py
python scripts/build_validation_2023_spot.py
python scripts/run_validation_2023.py
python scripts/report_validation_2023.py
```

Prepared/model/run version contracts reject changed code or inputs. The model cache
prevents an additional fit on identical reruns; execution trials remain recorded.
Do not change the strategy then overwrite these results.

- data/interim/validation_2023/v20261121_001/{prepared,spot_benchmarks,results}/
- results/{summary,run_contract,independent_verification}.json and all_runs.csv
- reports/tables/validation_2023/{primary_metrics,monthly_returns,all_registered_runs}.csv
- reports/figures/validation_2023/{lightgbm_dashboard,momentum_dashboard,shap_importance,cost_sensitivity}.png
- reports/acquisition/validation_2023_{prepare,spot,run,report,regression}_20261121.log

Original limitations remain: retrospective cohort/identity evidence, fractional
lot sizing, unvalidated exchange filters/liquidation, hourly VWAP fills and funding
mark proxy, current reference fees rather than verified historical account pricing.
No paper/live launch. Do not automatically open2024 or final OOS; discuss next
research choice using this frozen result. Any2023-informed changes make2023 part
of development for the modified strategy.
