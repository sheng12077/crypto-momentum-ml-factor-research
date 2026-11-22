# Experiment009: frozen expanding-window validation2023

Registered2026-11-21 before loading2023 market values, feature/label computation,
model fitting or performance inspection. User authorized opening2023 after the
2022 concentration diagnostic.2023 is the next validation window, not final OOS.
2024 and final2025-01-01/2026-11-01 stay sealed.

## Hypothesis and interpretation thresholds

Hypothesis: the fixed three-group LightGBM specification has useful net performance
beyond2022 and improves on an unfitted60day momentum portfolio of the same form.
Prespecified evidence gates: net return>0 and Sharpe_rf0>0 at primary5bps;
incremental-model support additionally requires net return and Sharpe above the
matched momentum control. Report MDD/Calmar/volatility without optimizing them.
Call evidence mixed if only some gates pass; never revise gates after inspection.
Report best-month share of additive annual PnL, all monthly returns, and product
of other months. If annual PnL>0 but removing the best month leaves nonpositive
compounded return, flag concentration dependence. These are descriptive gates,
not significance tests, profitability guarantees or strategy selection criteria.

## Fixed specification

- Same conditional37pre2021 cohort as005/008, no expansion/survivor reselection.
  Same dated lifecycle/data eligibility rules and identity caveats; preserve missing
  eligible observations, do not drop an asset based on2023 return or later survival.
- Expanding train2021-01-01 through2022-12-31; only labels with availability strictly
  before2023-01-01. Original corrected prepared_v003 training values unchanged.
  Seven-day execution-VWAP return label; one fit, same five inputs and PARAMS as005.
  No2023 label is used for fitting/early stopping/tuning; no within2023 refit.
- Score2023Mondays from information available before each decision, including2022
  warmup. No2024 source rows or labels. Predict2023 without computing2023 labels.
- Weekly top5long/bottom5short, equal10% of current NAV each, target gross100%,net0.
  Cash if fewer than20qualified; stable identifier ties; no buffer/voltarget/staging.
- Same Monday01UTC sizing/02UTC prior-hour VWAP fill, funding/marks/8decimal
  fractional filters as005; initial100000USDT,5bps taker, noBNB. Same conditional
  execution/funding/liquidation limitations; paper/live remains unapproved.
- Separate fresh-cash2023runs: LightGBM and unfitted60day momentum. Primary5bps,
  mandatory0/2/10bps cost sensitivities for both; retain all8cases. Financial replay
  primaryML5bps. No parameter search or favorable-case substitution.
- Match prior year-end convention: last NAV2023-12-31 00UTC, forced closeDec30
  23UTC at previous completed-hour VWAP. Report364daily returns explicitly, not a
  complete Jan1-to-nextJan1 return.
- BTC/ETH actual spot fixed-unit cash-budget hold on same calendar,5bps adverse
  fills and10bps spot taker, no leverage/funding. Same006benchmark identity.

## Data and engineering acceptance

Verify canonical source hashes; append2023only to a new version of prepared cache.
Never overwrite prior experiments. Same feature definitions; exact-value comparison
of preserved2021/2022 rows. Scope-filter source rows before feature computation;
no2024/final OOS values. Boundary metadata may be read for source verification.

Necessary source repairs may retrieve missing2023trade/mark source-days from public
official daily ZIPs with CHECKSUM, pacing>=1s, no silent forward fills or substitution.
Recover only missing keys where counterpart source exists; max200source-days,
400requests,64MiBcompressed,2MiB/ZIP,10MiBdecompressed/member. No overwrites of
existing source values. Stop on403/418/429; failures recorded and surfaced.
Spot acquisition24monthlyZIPs+checksums, max64requests/32MiBcompressed. No keys.
If bounds or source proof fail, stop without changing cohort/rules based on PnL.

Generalize only the engine calendar arguments; default005behavior unchanged.
Regression-test default2022 event calendar and2023 boundary/schedule/train purge
on synthetic data before running; hand-check funding/roundtrip in Nautilus runtime.
Daily NAV/cash/funding/fee ledgers within0.01USDT, final flat, no missing held marks
or executions, all outputs finite, every source input hash bound. SHAP on all2023
predictions with additivity error<=1e-6; interpret as model attribution, not causality.
Replay exact financial hash. Produce English notebook/report, charts, CSV/JSON.
Record failures/runtime/code/source hashes and all cases; no adjustments after
seeing results. An engineering failure may be fixed and rerun with explicit record,
never by changing the trading rule or deleting unfavorable results.
