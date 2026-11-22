# Experiment020: dynamic-universe first-window replay

Registered2026-11-22before new labels,model fitting or PnL. Existing historical years
are retrospective research,not fresh OOS. Firstwindow:train2021,trade2022only.

## Fixed design

- Use Experiment019dated provisional crypto rows,all historical identifiers retained;
  no fixed37cohort,whole-period availability filter or future-return selection.
- Freeze original five inputs(momentum20/60/120,funding7,imbalance7),including current
  conservative funding checks. No buffer,volatility overlay,extra factors or tuning.
- Train once on2021weeklyrows whose7dayVWAPreturn label matures before2022-01-01.
  Entry01-02UTC VWAP,exit same hour7days later;label available exitbarclose+1h.
  Missing labels are excluded with a reason ledger,never zero-filled.
- LightGBMregression:n_estimators100,learning_rate.03,num_leaves7,max_depth3,
  min_child_samples100,reg_lambda10,subsample1,colsample_bytree1,random_state42,
  deterministicCPU,force_col_wise,n_jobs1. Save model,trainrows,predictions,TreeSHAP,
  group absolute SHAP and additivity verification. No2022training or parameter search.
-2022Mondaydecisions every second Monday fromJan3;top5long/bottom5short,
  each +/-10%NAV,gross1,net0at rebalance;minimum20qualified names,else cash.
  Stable instrument-IDtie break. Actual quantities persist between rebalances.
- Regular orders decided01UTC using completed00-01close,filled02UTC against01-02VWAP
  as a conditional research execution proxy.100000USDTinitialbalance,leverage2.
  Nautilusaccount/order/fill/funding simulation;shared active accounting engine reused,
  never old37universe/model readers. Research fractional lots/ticks1e-8remain explicit
  approximations;not verified historical filters or tick-by-tick liquidation replay.
- VIP0current-cost assumption:taker5bps,noBNBdiscount. Adverse slippage5/10/20bps
  perfill;all registered cases reported. Not authenticated historical fee reconstruction.
- Controls:same-clock60daymomentum;equal3factor-group rankscore(momentum mean of
  three horizon percentile ranks,negativefundingrank,positiveimbalance rank);20random
  ranking seeds1000..1019,hash(seed,date,symbol),all at5bps. Deterministic controls
  also5/10/20bps. One5bpsMLdeterministic replay.30financial executions total.
- BTC/ETHspotbuy-and-hold benchmark:verified existing2022spot archives,10bpsfee,
 5bpsslippage,buyJan1 02UTC,sellDec30 23UTC. Strategy initialNAVJan1 00UTC,lastNAV
 Dec31 00UTC to match first-window prototype boundaries;last civil day is not traded.
- Funding actual recorded event times/rates,including verified repair rows even if
  interval metadata is not established;that metadata is not needed for event cashflow.
  No invented rates/zero imputation. Latest completed mark <=2hoursold required.
- Dated cessation policy:validate official futures-specific source/publication/effective
  dates for first-window candidate cessation episodes. No new entries after notice+5min;
  close an existing position at end of first full1minVWAPbar starting >=notice+5min.
  This scheduled riskexit is separately logged/costed and precedes official cessation.
  If price unavailable or exit not before cessation,block that affected case,never
  fabricate settlement or delete the asset's prior history. Publication vintage remains
  an assumption;do not use a spot or coin-margined notice for a USDTcontract.
- Cessation/repair integration changes are part of corrected dynamic-universe behavior;
  comparison to the old prototype is not a mathematically pure universe-only ablation.
- Preflight all planned cases together before long simulations:instrument creation,
  sizing/fill/held daily and funding marks,unknown recorded-schedule gaps,terminal risk
  exits and final liquidation. Collect all failures. Reuse checked recovery caches;
  official public missing-bar requests are bounded/resumable. Never quietly skip costs.
- Full2026funding uncertainty is outside this2022financialwindow;do not use its future
  gap flags to filter2022entries. Do not reveal new2023+PnL in this experiment.

## Acceptance and deliverables

Engineering success:reconciled NautilusNAV/cash/fees/funding/fills;allplannedcase
outcomes recorded,source/time checks,saved model/SHAP,primaryreplay,benchmarks,
English report/notebook,monthly returns and attribution. Profit is not a pass criterion.
Report return/CAGR/Sharpe/MDD/Calmar/costs/turnover,allrandomcontrols,and concentration
with/withoutbestmonth. No best-case selection or new clean-OOSclaim.

Prepare reusable CLI/config and meaningful synthetic/known-answer engine tests before
handing long execution to the user. Provide onecopyablecommand,logs/output locations,
success criteria and machine summary. Do not replace this deliverable with another
universe-count-only audit. Demonstrated unresolved source blockers stay explicit.
