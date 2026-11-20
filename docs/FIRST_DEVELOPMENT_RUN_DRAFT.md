# First 2021–2022 development run: specification draft

## Material Passport

- Origin:academic-research-suite/experiment-agent,plan mode.
- Date:2026-11-20.
- Status:PARTIALLY_CONFIRMED;no model fit or strategy performance executed.
- This is not full experiment preregistration or an executable configuration.

## Confirmed choices

The user explicitly selected momentum,funding,and aggressive trade imbalance
for the first development experiment. Size is excluded from this first selection
round and reserved for a separate later experiment;its historical publication
vintage remains unproven. Do not silently restore Size to the initial model.

The user confirmed NautilusTrader as the transaction/account simulation engine.
Feature engineering,chronological model fitting,SHAP and score generation live
outside the engine. Scores become portfolio targets;the strategy adapter turns
targets into simulated orders. Account state/commissions/funding are reconciled
once;the external performance report must not double-count engine cashflows.

Existing split and stage0clock stay unchanged. Development is2021–2022;an inner
2021train/2022validation is proposed before refitting for2023. Final2025Jan–2026Oct
OOS stays sealed. Model/portfolio choices must not use2023performance until the
promoted specification/selection procedure is frozen.

## Proposed first baseline defaults for review

| Item | Proposed specification | Status |
|---|---|---|
| Momentum |Separate20/60/120-day returns as model inputs;no fitting of four fixed factor percentages|draft|
| Funding |Past7-day observed rate sum,strictly before feature cutoff;coverage checked using reported intervals|draft|
| Aggressive imbalance |Past7-day ratio(2*taker-buy quote volume/total quote volume)-1;zero/missing denominator is missing,not neutral|draft|
| Models |Unfitted60-day momentum sorting reference and one small fixed-parameter LightGBM regression;SHAP required|draft|
| Target |Existing7-day forward execution-proxy return before costs/funding|stage0fixed|
| Portfolio |Long5/short5,equal weights within each side;targetlong50%/short50%NAV,gross100%/net0|draft|
| Insufficient names |Require20qualified names for reconstruction;skip/cash/retention treatment must be specified explicitly|draft|
| Main schedule |Weekly,no rank buffer or staged sizing in first engineering baseline|existing direction|
| Later candidates |2-week/4-week schedules and weekly buffer are separate registered comparisons|draft|
| Evaluation |NetNAVreturn/CAGR,Sharpe,volatility,MDD/recovery,Calmar,turnover,cost/funding attribution|discussed direction|
| Selection |Primary objective,numeric risk constraints,tie-breaks,and acceptance/failure criteria before performance|pending|

The numeric holdings above are proposals,not newly confirmed trading rules.
Net notional neutrality does not imply beta neutrality. Exact feature transforms,
all LightGBM parameters,entry/exit/tie/buffer rules,reweighting,forced exits,
cash accrual and treatment of unavailable marks must be frozen before a run.

## Nautilus execution requirements

- The current project pyproject.toml declaresPython>=3.13,<3.14and does not yet
  include NautilusTrader or LightGBM. Check compatibility and pin versions in a
  project-specific environment;installation/runtime availability is not claimed.
- Use the appropriateCryptoPerpetual/margin instrument/account models forUSDT
  perps. Funding settlement depends on supplied event data and boundaries;the
  engine cannot infer missing historical fees,funding marks,or trading rules.
- Test positive/negative funding for longs/shorts,positions opened/closed around
  boundaries,and non-exact-boundary source timestamps before whole-portfolio runs.
  Historical realized funding must not become a feature before its availability.
- Stage0Monday01–02hourVWAP is an unverified research execution proxy,not an
  automatic Nautilus default or proof an order could fill atVWAP. Freeze an
  explicit bar/quote adapter and fill model or register a revised timing proxy.
- Default no probabilistic slippage is not our cost assumption. Maker/taker
  commissions,adverse fills,order-size/volume limits and cost stress cases need
  explicit configuration. Bar-only data does not reconstruct historicalL2depth.
- Before performance,run deterministic tiny trade/accounting scenarios against
  hand-calculated expected fills,fees,funding andNAV. This validates integration;
  it does not authorize another full research backtester or paper/live trading.

Official references checked2026-11-20(latest docs,not a pinned installed version):
[Fill models](https://nautilustrader.io/docs/latest/concepts/backtesting/fill-models/),
[Accounts and funding](https://nautilustrader.io/docs/latest/concepts/backtesting/accounts-and-margin/).

## Remaining data prerequisites

The latest38of40identity release covers2020/81early IDs only. Establish the
2021–2022universe/identity validity and2020-to2021warm-up continuity before
applying these features. Size exclusion removes one input requirement;it does
not prove all other historical eligibility/execution assumptions. Current
performance_enabled/oos_access_enabled flags remainfalse;no results are claimed.
