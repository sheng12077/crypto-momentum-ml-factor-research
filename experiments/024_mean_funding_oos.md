# Experiment 024: user-authorized adjacent-mean funding scenario

Registered 2026-11-23 before scenario implementation or financial execution.
User explicitly requests average imputation to inspect the original OOS interval.
Amend Experiment 023 only as follows; preserve its strict run/config and source data.

2025 remains the unchanged strict annual account. 2026 January–October is a
separate assumption-based account. Both LightGBM and equal-factor-group portfolios,
all original cost/control cases and primary replay remain registered: 30 per year.
All parameters, dated selection, source hashes and non-funding checks are unchanged.
No other imputation scenarios are added in this work segment.

For internal funding gaps whose inferred missing event times fall exclusively on
2026-06-24 UTC, require adjacent original observations with the same positive
reported funding interval and timestamps consistent with that interval's grid
(allow existing <=1000ms exchange jitter). Insert every inferred missing nominal
event using (original preceding rate + original following rate)/2. Use original
anchors only; never recursively average synthetic rows. If intervals change or
anchors/times cannot be reconciled, leave the gap blocked. No tail extrapolation,
other-day filling, altered settlement evidence, or fabricated original records.

Imputation is for simulated accounting only and occurs after model fitting.
Daily factors, labels, training data and ranked schedules do not consume imputed
rates. Following-anchor rates are future information at the estimated event time;
this is explicitly a retrospective cost assumption, not real-time observability.
Its cashflows affect subsequent NAV and order sizes as in normal accounting.

Keep raw/canonical/prepared funding observations unchanged. Save a distinct
scenario config/run and a source-bound assumption manifest with both anchors,
reported intervals, synthetic times/rates and the future-anchor flag. Do not
claim the estimates establish that a real payment occurred. Disclose scenario
and estimated cashflow usage in report, compact summary and notebook.

Acceptance: both annual preflights pass under their respective declared rules;
all 60 financial cases and yearly primary replay pass; independently reconstruct
each estimated rate/time from original anchors, then verify fills, funding and NAV.
No gate waiver for unresolved tails, price omissions, unrelated funding breaks or
cessation facts. Disclose failures and performance regardless of profitability.
No acceptance threshold changes after performance. Agent performs small tests;
user executes full preparation/training/simulations. Retain original OOS dates
and separate annual-account boundaries; do not claim continuous-account results.
