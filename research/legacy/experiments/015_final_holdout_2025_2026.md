# Experiment 015: frozen final holdout, 2025 and January--October 2026

Registered before implementation or loading final-window market values, fitting,
labels or PnL. User authorizes opening this final holdout and will execute it.
Agent scope: implementation, synthetic validation and unexecuted English notebook;
no historical preparation, fits, benchmarks or simulations during handoff.
2024 failed validation and remains visible. No new strategy selection/tuning.

## Frozen strategy and annual learning

Same conditional37identifier cohort, dated eligibility and five raw features as
013:momentum20/60/120,funding7,imbalance7. Same original LightGBM PARAMS,7day VWAP
return label,5long/5short,equal10%NAV,net0/gross100%target,no buffer/timing/extra
filters/Size. First Monday of EACH year anchors every14days; actual quantities
held between decisions. Fewer than20eligible means cash. Stable identifier ties.
Same01UTC sizing,02UTC prior completed-hour VWAP,5bps taker fee,noBNB,5bps primary
extra adverse slippage and10bps stress; initial100000USDT.

Fit2025once with2021--2024features and labels strictly available before2025-01-01.
Fit2026once with2021--2025features and labels strictly available before2026-01-01,
regardless of2025performance. Fill only missing matured historical labels from
verified execution-hour data; preserve every previously known label and feature.
Filter before label-price lookup; no2026training labels,early stopping,tuning or
within-year fits.2025validation features stay unlabelled;2025labels used for2026
are separately materialized training rows. No retrospective forecast selection.

## Twelve cases and continuous trading

ML and matched unfitted momentum60 control x5/10bps x three windows =12cases.
Standalone2025:Jan1--Dec31 00UTC NAV,365snapshots/364returns,forced closeDec30 23UTC.
Standalone2026:Jan1--Oct31 00UTC NAV,304snapshots/303returns,forced closeOct30 23UTC.
These retain013's last-day-midnight/previous23UTC liquidation convention; report
that they omit the final civil day's return, rather than claiming complete years.

Continuous:Jan1 2025--Oct31 2026 00UTC,669snapshots/668returns,forced closeOct30
23UTC2026only. No2025year-end flattening/cash reset;2026new model changes targets
on its first scheduled decision. Report continuous full metrics and year slices;
continuous2025slice includesJan1 2026snapshot,continuous2026starts at that snapshot.
Do not compound standalone cases into a purported live equity curve.
Replay primary ML for each of three windows:3identical financial hashes required.

BTC/ETH actual spot fixed-unit cash-budget holds in each window,10bps spot taker
fee plus5bps adverse fills,noFunding/leverage. Continuous benchmarks keep units
across year-end. All comparisons share exact snapshot calendars. Report2026and
continuous cumulative returns separately from365dayannualized CAGR/Sharpe.

## Gates and interpretation

No new acceptance thresholds: positive net return AND Sharpe_rf0 at5bps; positive
net return at10bps; primary return AND Sharpe exceed matched momentum60. Report
per window, not cherry-picked. Report MDD/Calmar/volatility,fees,funding,notional,
monthly and year-sliced performance,best-month concentration,all three SHAP groups.
Exclude-best-month sensitivity is descriptive only. A positive period does not
erase2024or establish deployability. No timing/filter/short-selection changes or
paper/live deployment. This holdout is consumed once results are inspected.

## Source scope and bounded recovery

Use existing verified2024prepared data read-only. Canonical daily projection:
2024-08-01 <= day <2026-11-01; hourly2025Jan--2026Oct only, plus old warmup.
Hash files without loading later values. No2026Nov/Dec market rows, labels or PnL.
Keep dated lifecycle blocks; never join reused identities or discard poor assets.
Missing held marks/executions or unsupported lifecycle settlement fails visibly;
no fabricated settlement, forward fill or retrospective cohort substitution.

Optional necessary trade/mark missing-key repair:official public daily ZIP plus
CHECKSUM,<=200source-days/400requests/64MiBcompressed,2MiBZIP/10MiBmember,>=1s pacing;
stop on403/418/429,never overwrite original values. Spot44monthlyZIPs+checksums:
<=128requests/64MiBcompressed,2MiBZIP/10MiBmember. Normalize official spot2025+
microsecond timestamps to UTCms with recorded source units and boundary checks.
No credentials. Failed requests consume budgets; failures/provenance retained.

## Engineering acceptance and handoff

Register source/code/runtime contracts and per-case hash completion markers;
resume only verified immutable caches. Persist attempt logs and failed attempts;
never bypass mismatches by deleting contracts. Keep previous results unchanged.
Synthetic tests must cover strict two-fold purge,previous missing labels,exact
known-label preservation,no future lookup,unchanged2024feature definition,
53/52week calendar phases,partial2026end,year-end position continuity,spotus/ms
normalization,fee/funding/NAV reconciliation and detection of result corruption.

DailyNAV=cash+unrealized and fees/funding/notional within0.01USDT,finite positive
NAV,final flat,no held missing prices,exact3financial replays. SHAP on all scored
rows,additivity error<=1e-6; no causal-profit claim. Independently reconstruct
training rows/predictions/targets and completed case hashes. English report,
unexecuted notebook at handoff (execute saved-result cells after user run),CSV,
figures,compact JSON,copyable WSL commands/log paths and realistic runtime caveat.
