# First historical development run

## Material Passport

- Origin:academic-research-suite/experiment-agent;integrated code experiment.
- Date:2026-11-21. Registrations:005(0cf6127),006(63aefa0),007(53e75f2).
- Status:engineering execution and financial replay VERIFIED;economic result is
  conditional development validation, not certified alpha or live readiness.
- Scope:fixed37symbol cohort derived from reviewedpre2021records;2020warmup,
  2021training and2022validation only. No2023/2024/finalOOSperformance inspected.

## Outcome

The full data-to-model-to-Nautilus-to-notebook pipeline has actually executed.
Eight registered strategy/cost cases completed;the primary2022case replayed with
identical normalized financial outputs. Model hash and all2021training values
remain unchanged after the data repairs;only one model was fitted.

2022primarycase:5bpsadverse extra slippage perfill,taker0.0005,noBNB,
commissions and modeled funding included,100000USDTinitialcapital:

| Series | Total return | DailySharpe(rf0) | DailyNAVMDD |
| --- | ---: | ---: | ---: |
| LightGBM long5/short5 | +22.24% | 1.031 | -14.09% |
| BTCspot-pricehold | -64.63% | -1.310 | -66.93% |
| ETHspot-pricehold | -67.97% | -0.876 | -74.01% |

Ending strategyNAV122242.16041289USDT;841fills;10850fundingcashflows;
4048.71864862USDTcommissions;netfundingcredit1310.08931476USDT.
Ledger reconciliation error approximately1.46e-11USDT.

| Extra adverse slippage perfill | 2022MLreturn | Sharpe | MDD |
| --- | ---: | ---: | ---: |
| 0bps | +26.61% | 1.192 | -13.60% |
| 2bps | +24.85% | 1.128 | -13.71% |
| 5bps, preregisteredprimary | +22.24% | 1.031 | -14.09% |
| 10bps | +18.02% | 0.869 | -14.75% |

The unfitted60daymomentum baseline lost68.82%over2021–2022at5bps(Sharpe-1.037,
MDD-74.36%). This is a different period and must not be compared directly with
2022MLas a same-window model ranking. All four losing baseline cases remain saved.

## Completed data integration

- Source-bound daily/hourly caches and2020warmup integrated with the verified
  development mark overlay. Original canonical releases remain unchanged.
- Full execution-key preflight exposed1440missingtradehours in12cohortsymbols
  on2022-02-26/27/28and2022-04-01/02. All60officialdailyZIPs+checksums restored
 1440/1440keys.2021features/labels stayed exactly equivalent;2022features rebuilt.
- Final feature panel3841rows:1880purgedtraining samples,1924validation samples
  and37late2021feature rows whose forward labels are unavailable before2022.
  Finalweeklycoverage36–37(median37);all52weeks of2022have37candidates.
- Metadata note:prepared_v003manifest inherits the original cache's three
  weekly_candidate_*diagnostic counters. They describe the pre-trade-repair
  cache and are not used for selection. The authoritative post-repair counts
  are recomputed directly in results_v003/final_coverage.json.
-37cohortfunding interval preflight foundno gaps;observedrates are features only
  after1hourlag. Settledcashflows use recorded eventtimestamps and a completed
  mark-hourclose proxy,not a claim that actual historical fundingmarks were proven.

## Model and research assumptions

Inputs:20/60/120daymomentum,past7dayfunding-rate sum,7dayaggregate aggressive
quote imbalance. LightGBM fixed100trees,depth3,7leaves,learningrate0.03,
min_child_samples100,L2=10,CPU1thread,seed42,deterministic. Train2021only;
latest training label available2021-12-27at03UTC,before2022cutoff.
SHAP computed for every2022sample;additivity error8.33e-17.
Grouped mean-absolute SHAP:momentum0.01719,funding0.00530,imbalance0.00436.
These are model attributions, not causal effects or portfolio allocation weights.

Weeklytop5long/bottom5short,equalweights,targetgross100%/net0,minimum20names.
Quantity sizing uses information knownMonday01UTC;fills occur02UTCat the
completed01–02hourVWAPplusadverseprice. Funding is a custom Nautilus simulation
module and fees/cash/position/unrealizedPnL are reconciled, not double-counted.
Positions close2022-12-30at23UTC;lastdailyvaluation2022-12-31at00UTC.

Material limits:retrospective fixed-cohort evidence availability and same-symbol
identity continuity remain conditional;fractional lot/tick assumptions, no verified
historical exchange filters/L2/liquidationmodel;VWAPandsettlementmarkproxies;
current reference fees rather than historical account/promotional schedules.
2022is a development validation period, not untouched finalOOS. Positive return
does not establish broad-market alpha or readiness for real money.

## Benchmarks and preserved failed attempts

The first fundedBTCperpetualhold benchmark became nonpositive inNovember2022
after accumulatedfunding. Its failed logs/ledgers remain underresults/and
diagnostics/btc_accounting/. It is not relabeled as a spot benchmark or repaired
by removing funding. Before any valid strategy result was inspected,registration006
replaced the primary comparison with official BTC/ETHspot-price passivehold.
48monthlyspotZIPs+checksums verified;8partialmaintenancehours quarantined;
all predetermined entry/exit/valuation hours present. Spot fee reference0.001,
5bpsfills,noBNB,no funding, no leverage. Passive fixed-unit accounting is not a
second strategy backtester or a claimed Nautilusspot-exchange simulation.

The second run failed on missing2022trade execution inputs;results_v002/and its
logs remain intact. Registration007fixed source data only. The original model was
reused after verifying identical training rows and parameters;2022SHAP/predictions
were recalculated on corrected past inputs with no refit or parameter changes.
Finalresults_v003contains all successful cases. Nothing was cherry-picked into
a profitable promotion winner;engineering success was the registered threshold.

## Open results

Open notebooks/first_historical_results.ipynb and RunAll. It is fully English and
reads actual saved historical results. The old synthetic notebook/useroutputs
were not overwritten. The new notebook has already executed all5codecells.

- Executed copy:reports/acquisition/first_historical_results_executed.ipynb.
- Plots:reports/figures/first_development/.
- Tables:reports/tables/first_development/.
- All cases:data/interim/first_development/v20261121_001/results_v003/all_runs.csv.
- Source/feature cache:.../prepared_v003/.
- Model/SHAP:.../results_v003/model/.
- Trades/funding/targets/dailyNAV:eachmodel/slippage_<bps>bps/.
- Independent checks:.../results_v003/independent_verification.json.

PowerShell, from the repository:

```powershell
py -3.11 scripts/run_first_development_launcher.py --stage report
py -3.11 scripts/run_first_development_launcher.py --stage verify
# Re-execute all eight cases from the already verified caches, no market download:
py -3.11 scripts/run_first_development_launcher.py --stage all
```

Runtime:isolatedWindowsCPython3.13.18under userTEMP/momentum_development_005/venv;
lockedrequirements/development-windows-py313.lock. The wrapper can recreate it
without modifying the borrowed conda or existingWSLruntimes. WSLservice launches
timed out during this run,so nativeWindowswas used;do not assume aLinux financial
hash will be bit-identical under different binaries. Notebook reporting needs only
the existingpandas/matplotlibkernel,not LightGBM fitting.
The launcher is Python because Windows requires signedPowerShellscripts on this
UNCshare. No execution-policy or service setting was changed.

Verification:independentall8cash/NAV/fee/funding/benchmark checks passed;
primary2022financialreplayidentical;14isolatedengine/reporttests passed;
nativeprojectregression271passed/2skipped(Nautilusabsentthere);Ruffpassed.
Monthlybar plotting was visually corrected for pandas/matplotlibcompatibility;
all8metrics were asserted unchanged while refreshingcharts.

Official technical references:
[LightGBMdeterminism](https://lightgbm.readthedocs.io/en/latest/Parameters.html),
[TreeSHAP](https://shap.readthedocs.io/en/stable/generated/shap.TreeExplainer.html),
[Binancepublicarchives](https://github.com/binance/binance-public-data),
[spotreferencefees](https://www.binance.com/en/fee/trading).
