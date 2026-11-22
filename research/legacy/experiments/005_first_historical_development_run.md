# Experiment 005: first end-to-end historical development prototype

Registered2026-11-21before implementation, fitting or strategy PnL inspection.
The user requests an end-to-end deliverable rather than further isolated audits.
This is a conditional research prototype, not a certified PIT universe or live
trading qualification. It explicitly revises earlier engineering-only gates;
strict identity/publication/contract/funding certification flags stay false.

## Fixed population and data

- Fixed pre2021venue-symbol cohort:the40corroborated rows in the frozen2020
  asset_review release, excluding BCHUSDT(unresolved fork bridge),KNCUSDT
  (underlying conversion) and LENDUSDT(ended legacy contract). Expected37symbols.
  This is not selected using2021–2022returns or later survival. Do not silently
  describe2020evidence scopes as2021–2022proof;same-symbol underlying continuity
  in2021–2022is an explicit unresolved research assumption. No provider Sizejoin.
- Load2020warmup and2021–2022only, integrate the new verified2901hour overlay
  explicitly, and hash-bind consumed daily/hourly sources. No market downloads
  or2023onward values. Preserve old canonical files and user notebook outputs.
- Build weekly features:20/60/120dayclose returns with121valid consecutive
  closes;past7day observed funding-rate sum;7dayaggregate aggressive quote
  imbalance(2*buyquote/quote)-1. Require valid7dayinput coverage and latest
  funding freshness. Observed funding becomes a feature only after1hourlag;
  no future/missing fill or division-by-zero substitution.
- Features use data strictly before Monday00UTC;decisionMonday01UTC. For
  quantity sizing use only the latest fully closed hour at01UTC. Model labels
  are forward7dayexecution-VWAP returns, known no earlier than nextMonday03UTC.
  Training labels must be available before2022-01-01, with boundary purge.

## Fixed models, portfolio and execution

- Unfitted60daymomentum ranking baseline,2021–2022. Separate LightGBM regression
  trained once on eligible2021weekly samples and evaluated2022only;no2021fitted
  model PnL, no tuning/feature/model selection, no2023/2024/finalOOSinspection.
- LightGBM:n_estimators100,learning_rate0.03,num_leaves7,max_depth3,
  min_child_samples100,reg_lambda10,subsample1,colsample_bytree1,random_state42,
  deterministicCPU,1thread. Inputs are the five raw features above;no fixed
  factor-weight optimization. Save model, training sample/label provenance and
  validation SHAP values, mean absolute SHAP and additivity check.
- Weekly top5long/bottom5short, equal side weights;50%long/50%short NAV,
  gross100%,net0at rebalance. Require20qualified names;otherwise targetcash.
  Stable tie-break:instrument ID. No rank buffer, staged sizing or vol overlay.
- Orders:quantities decided01UTC from known reference prices/NAV;simulate
  arrival/fill at02UTC against the completed01–02VWAP, not before the hour is
  known. This makes stage0proxy timing explicit and is not a claim of executable
  VWAP. Missing execution price for a required trade is a hard run failure.
- Actual Nautilus account/order/fill/position path;no parallel PnL backtester.
  Starting100000USDT,margin account,leverage2,gross1. Fractional research lots
  and price ticks1e-8;historical symbol filter/lot specifications unverified.
  Market fills,taker0.0005,noBNB;maker reference0.0002unused. Current-cost replay,
  not account-authenticated or historical fee reconstruction.
- Identical frozen signals, adverse extra slippage0/2/5/10bpsperfill;primary
  reporting case5bps,all cases retained. No selection of the best cost scenario.
- Funding:all actual archive events at their exact recorded timestamps, including
  jitter;positive rate debits long/credits short. Settlement mark proxy is latest
  completed mark-hour close, at most2hoursold;missing/staler held-position mark
  fails. Snapshot positions before same-timestamp orders. Use engine account
  adjustment extension and separate cashflow ledger. This is explicitly modeled
  settlement, not proof of historical paid cashflow;never omit funding silently.
- NAV:enginecash plus engine-position unrealized_pnl at latest available marks,
  once daily at00UTC. Missing/stale held marks or rejected/unfilled required
  orders fail. Reconcile commissions/funding/cash/realized/unrealized PnL.
- Forced final close2022-12-30at23UTC(previous22–23hourVWAP),last NAV2022-12-31
  at00UTC;last partial weekly holding truncated. Initial snapshot is cash.
- Benchmarks:BTCandETHfunded perpetual buy-and-hold simulated by the same
  engine/cost assumptions,enterfirstday02UTC,closeasabove. They are explicitly
  perpetual proxies, NOT spot buy-and-hold. Spot data/fees remain a later benchmark.

## Acceptance and reporting

Acceptance is an executable integrated pipeline, source/temporal checks, actual
engine fills with fees/funding, finite reconciledNAV, saved SHAP and notebook
outputs. Profitability is NOT an engineering pass criterion. Report all registered
runs, including losses/failures;no promotion winner or statistical alpha claim.
No missing-data/rule/parameter changes based on observed strategy performance.
Independent known-answer tests precede history. Run one deterministic replay of
the primary2022case and compare normalized financial outputs/hashes.

Output:versioned prepared data/features/labels,sources/assumptions manifest,
model/SHAP,2021–2022momentumbaseline,2022MLvalidation,all cost scenarios,BTC/ETH
perpetual benchmarks, daily/fill/funding/target tables,metric/PNG/CSVexports and
an executable English results notebook. Stop only at this deliverable or a
concrete demonstrated execution blocker;do not substitute another audit-only
handoff. Paper/live and untouched OOS remain outside scope.
