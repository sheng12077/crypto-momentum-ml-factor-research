# Experiment010: bounded execution and feature diagnostics

Registered before implementation/execution. Both2022and2023results have already
been inspected and now serve as development data.2024and final2025–Oct2026remain
sealed. No new data/universe expansion, hyperparameter search, new factor feeds,
label horizon changes or short-only/regime/timing strategy in this experiment.

## Fixed two chronological folds

2021train ->2022evaluate;2021–2022train ->2023evaluate. For each fold, training
feature cutoff and label availability must be strictly before January1of the
evaluation year. Reuse verified prepared_v003/Experiment009 sources. Same37cohort,
seven-day label, PARAMETERS,5long/5short,gross100%/net0target,fees/funding,VWAP
execution and year-end convention as005/009. Expanding folds are not independent
untouched tests after this selection exercise.2023labels are not computed.

## Eight configurations, no Cartesian product

A: original full-feature weekly model, cached reference at5/10bps per fold.
B: full-feature weekly model with symmetric rank buffer: enter top/bottom5,
retain existing names while in top/bottom8 of CURRENT eligible cross-section.
Keep at most5per side, fill vacancies from top/bottom5 in rank order; stable symbol
ties as original. No overlap. Fewer than20eligible =>cash/reset retained names.
Rebalance retained targets back to equal+/-10%NAV weekly: buffer reduces membership
changes, not all resizing turnover. Rank eligibility uses only current features.
C: same full-feature scores, rebalance every2weeks.
D: same full-feature scores, rebalance every4weeks.
Cadence phases are fixed from firstMonday each year (2022Jan3/2023Jan2), indices
0,2,... or0,4,...; no alternate phase search. Between scheduled dates keep actual
quantities, no equal-weight resizing. Weekly scores still exist; no new14/28day
forecast label or model. Availability/eligibility is reconsidered at scheduled
decisions; held missing-mark/execution errors must fail, never silently fill.
E: Funding-only weekly ranking, score=-funding7 (low funding long, high funding
short), a priori carry direction; no fitted model or testing opposite sign.
F: weekly LightGBM without the entire20/60/120momentum group.
G: weekly LightGBM without Funding feature (all actual funding cashflows retained).
H: weekly LightGBM without aggressive-imbalance feature.

Always execute both stages irrespective of first-stage results. B/C/D reuse each
fold's original model/predictions exactly. F/G/H each fit once per fold on identical
training rows/labels and unchanged PARAMS, dropping only specified columns.
Compute full-validation SHAP/additivity for all6new fitted models. Retain all runs.
All configurations at5bps primary and10bps stress:32cases total,4cached A cases,
28new actual Nautilus simulations. Financial replay B5bps in both years. No extra
slippage/parameter variants are chosen after observing these results.

## Expectations and acceptance thresholds

Execution hypothesis: buffer/slower updates reduce traded notional but may lose
forecast timeliness. A supported execution candidate requires in BOTH years:
positive net return, Sharpe greater than A, MDD no worse than A, and traded notional
below A at5bps. If none passes, report no supported execution improvement. Record
10bps outcomes and flag any nonpositive stress-year result as cost fragile.

Report best-month cash share and other-month compounded return for all cases;
flag positive years whose other-month compounded return<=0 as concentrated. Do
not present a candidate as broadly robust while such concentration persists.

Feature hypotheses: compare E/F/G/H against full-model A at the same weekly
schedule/cost/year. Consistent ablation direction requires Sharpe differences of
the same strict sign in BOTH years; otherwise describe mixed/no consistent evidence.
SHAP is prediction attribution, not causal PnL. Funding cashflow is never removed
when removing a predictive feature. No automatic factor deletion or combined
ablation/buffer/cadence variant is authorized here.

Engineering acceptance: input/model/source hashes bound; exact reused A financial
hashes; verify same full-feature scores for B/C/D and same training rows for F/G/H;
all held execution/mark availability enforced; final positions flat; daily NAV=
cash+unrealized and fee/funding/notional ledgers within0.01USDT; finite positive
NAV; replay financial hashes equal; SHAP residual<=1e-6. Unit tests cover rank
retention/entry/exit/reset/ties, phase/quantity holding, temporal purge and funding
accounting. Report failed runs without changing strategy to make them pass.

Deliver English notebook, all32results/costs/monthly/concentration/pairwise tables,
figures, verification and concise project handoff. Preserve prior results and user
notebook edits. Conclude this bounded experiment before any next-window request.
