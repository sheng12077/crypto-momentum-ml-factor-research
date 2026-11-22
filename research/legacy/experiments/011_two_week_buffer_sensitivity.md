# Experiment 011: two-week rank-buffer sensitivity

Registered before implementation or candidate backtests. User requests runnable
files and will execute the full experiment. Agent may run unit/synthetic engine
tests and prepare schedules, but must not execute full historical candidate runs.
Both 2022 and 2023 are inspected development years; 2024 and final OOS stay sealed.

## Fixed grid and interpretation

Same Experiment010 C_two_week models, five features, scores, cohort, forecast label,
fees/funding, execution, first-Monday phase and year-end convention. No new fits,
factor signals, data, SHAP inference or model tuning. Reuse original SHAP because
the models and prediction rows are unchanged. No new feeds/downloads/API keys.

Entry remains top/bottom5; retain previously held eligible names through ranks:
5 (no buffer control), 6 (width1), 8 (width3), 10 (width5). Rank is measured from
the appropriate long/short end of the CURRENT eligible cross-section. At least20
eligible names, at most5positions per side, no overlap. Stable symbol tie policy
as010. Fill vacancies from entry top/bottom5; any previously held asset absent from
current eligible set cannot be retained at a scheduled rebalance. Below20 =>cash
and reset membership. No maximum holding period or arbitrary score/trend threshold.

Check ranks and resize retained positions to equal+/-10%NAV ONLY every two weeks,
anchored Jan3 2022 / Jan2 2023 (calendar indices0,2,...). Between those decisions
keep actual quantities; no weekly buffer exits or resizing. Exit/entry gates are
distinct from holding more names: there are still five long/five short slots.

Four settings x two years x 5/10bps slippage =16cases. Reuse four verified010C
control cases, execute12new actual Nautilus simulations. Replay rank8/5bps both
years (two additional simulations). No threshold refinement after looking at
results; do not select on the highest annual return or open2024 automatically.

Hypothesis: wider retention can reduce membership turnover but may keep weaker
names longer, so performance/MDD need not improve monotonically. Report all sizes,
membership exits/entries, actual traded notional, fees/funding, Sharpe/MDD, monthly
concentration and both cost scenarios. Membership turnover and resizing turnover
are different; buffer does not eliminate equal-weight resizing at each decision.

A supported candidate requires in BOTH years at5bps: positive net return, Sharpe
strictly above rank5control, MDD no worse, traded notional below control, and
other-best-months compounded return>0. Additionally require positive net return
at10bps both years. List all passing settings, not just the best. Report whether
neighboring tested ranks also pass; an isolated peak is weak sensitivity evidence.
If none passes, keep the no-buffer control as the research baseline. No automatic
strategy config replacement or next-window execution is authorized here.

## Engineering and handoff acceptance

Original010 and model/data caches remain read-only. Bind all input, source model,
code/config and runtime hashes; reject incompatible resume. Native Windows/WSL
launchers must permit explicit --python, log stdout/stderr, propagate nonzero exits,
and avoid silently installing/updating packages. No secrets or raw data committed.

Unit tests: rank5 equivalent to010no-buffer; rank8 weekly equivalent to010buffer;
buffer width/boundary/missing-eligible/cash-reset/ties/overlap; two-week phase and
holding quantity. Synthetic Nautilus pilot exercises rank retention, actual skipped
week quantities and funding accounting, and must never output historical PnL.
Prepare-only may verify cached inputs/models/schedules without new historical runs.

Full user run: verify all16case keys, cached control financial identities, actual
schedule/weights/trade dates, final flat positions, finite positive NAV, daily
cash+unrealized equality, fees/funding/notional within0.01USDT, two financial replay
hashes identical, source model/predictions unchanged and no sealed-period access.
Checkpoint successful cases with hashes; resume must verify before reusing them.
Retain failed/partial attempts. Reports expose incomplete state; success=true only
after all16cases and both replays verify. Deliver English notebook, full tables/
figures, compact JSON summary, copyable commands/log/result paths and status handoff.
