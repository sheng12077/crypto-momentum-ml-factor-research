# Experiment 012: allocation within fixed selected names

Registered before implementation or candidate performance. User authorizes this
weighting experiment and explicitly keeps later windows sealed until research is
ready. Use only existing inspected2022/2023development folds and prior warmup.
No2024or final2025–Oct2026values/performance; no next-window run or paper trading.

## Fixed design

Keep Experiment010C_two_week's exact models, scores, cohort, selected5long/5short,
first-Monday two-week phase, seven-day label, execution/fees/funding and year-end
calendar. No buffer, new signal, eligibility filter, training, horizon change,
prediction recalibration, added leverage or within-holding-period resizing.

Three allocations only, normalized independently to long+50%/short-50%NAV:

- EQ: equal10%NAV per name, cached verified010C control.
- IV60: inverse standard deviation of the last60simple DAILY returns (61complete
  daily closing prices), sample ddof1. Each price must be completed/available at
  or before feature cutoff Monday00UTC; hourly close at23UTC is available next00UTC.
  Require consecutive61daily closes and finite positive prices. Missing input
  fails preflight; never drop/reselect a name or forward-fill. Floor daily sigma
  at0.005; rawweights=1/max(sigma,.005). Cap each absweight at15%NAV and redistribute
  remaining side budget proportionally among uncapped names, until side total50%.
- RANK: within each selected side, strongest long/weakest short receives side
  budget shares25/22.5/20/17.5/15%, or absNAV weights12.5/11.25/10/8.75/7.5%.
  Use original stable identifier tie handling. Do not treat raw scores as calibrated
  probabilities/returns. This ratio is a fixed hypothesis, not a paper's optimum.

All sides retain exactly the original membership. Apply targets only on scheduled
dates; hold actual quantities between dates. Gross target100%, target net0 does
not imply beta neutrality or equal portfolio risk across variants. IV60 is not
full equal-risk contribution because it does not estimate correlations. No search
over volatility windows, floors/caps, rank ratios or their combinations.

Three variants x two years x5/10bps extra slippage =12cases. Four cached EQ controls,
eight new actual Nautilus histories; replay IV60/5bps in both years. New model fits0;
reuse unchanged cached original SHAP. Retain all results, including negative ones.

## Questions and gates

Hypotheses: IV60may reduce dominance of high-volatility names; RANKmay benefit if
within-selected-name ordering is informative. Either can worsen costs, exposure,
concentration or net performance. Literature motivates the questions, not outcomes.

Report netreturn/Sharpe_rf0/MDD/Calmar/annualizedvolatility, fees/funding/notional,
monthly concentration, maxabsweight and effective name count per side1/sum(p_i^2).
Do not declare greater raw return a benefit if it only reflects higher risk.
Do not retrospectively scale using full-sample volatility for a tradable comparison.

Supported candidate gate in BOTH years at5bps: positive net return, strictly higher
Sharpe than EQ, MDD no worse, other-best-months compounded return>0. Also require
positive netreturn at10bps BOTH years. Record return/risk/cost tradeoffs even if
none passes. No automatic baseline replacement or next-window exposure.

## Engineering acceptance

Original source/model/input caches stay read-only, hashes bound; use a new output
version. Verify EQ schedule/financial identities against010C; all variants must
have identical selected names and decision dates. IV weights use only a scoped
daily-close input table with availability timestamps; future perturbation must
not change prior weights. Boundary61observations, floor, capped redistribution,
side budgets, short ordering/ties and unchanged between-date quantities tested.

Prepare weight/risk audit before simulations; validate all risk inputs before any
candidate PnL. Pilot on synthetic prices/holdings plus focused regression tests.
Cases require actual fills, funding, marked NAV/cash/fees/notional reconciliation
within0.01USDT, final flat, finite positive NAV and exact financial replay hashes.
Produce English notebook, all12cases and paired/monthly/weightaudit tables, figures,
verification and concise status. No favorable-case deletion, new filters or
parameter tuning after observing results; document engineering failures separately.

References motivating design (no claim of crypto long/short validation):
DeMiguel/Garlappi/Uppal(2009),doi:10.1093/rfs/hhm075;
Maillard/Roncalli/Teiletche(2010),doi:10.3905/jpm.2010.36.4.060;
Garleanu/Pedersen(2013),NBERw15205/workpaperdoi:10.3386/w15205.
