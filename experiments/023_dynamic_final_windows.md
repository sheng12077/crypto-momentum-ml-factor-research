# Experiment 023: fixed model and equal-factor scores, 2025–2026

Registered 2026-11-22 before implementing or executing this expanded-universe
evaluation. Preserve the original final-OOS date assignment, all earlier results
and the research history. No parameter selection within these windows.

Evaluate both previously registered LightGBM and equal-factor-group scores without
choosing a winner in advance. Hypothesis: either may retain positive cost-adjusted
performance; the learned model must demonstrate incremental value against the
simple score rather than being assumed superior.

Two independent annual accounts, each initially 100000 USDT:

- 2025: train 2021–2024, forecast/trade 2025, final NAV 2025-12-31 00:00 UTC.
- 2026 partial: train 2021–2025, forecast/trade through the available October
  boundary, stop_exclusive 2026-11-01, final NAV 2026-10-31 00:00 UTC.

Use only labels mature strictly before the forecast-year start. Keep each model
fixed during its trading year. Preserve the prior end-boundary convention, which
excludes the last civil day's returns. These accounts do not establish continuous
2025–2026 compounding or a no-reset drawdown statistic.

Inherit Experiment 022 strategy/model parameters, three factor groups, dated
universe, equal 5L/5S position weights, two-week January-anchored cadence, minimum
20 candidates, costs, 5/10/20 bps slippage, 20 random seeds and primary replay.
Keep momentum60 as a secondary matched control. Thirty financial runs per year,
60 total. No buffer, new factors, score tuning, portfolio weighting or regime gate.

Partial-year schedules must stop before the configured final close. Verify
source-bound official cessation facts and post-notice prices; preserve pre-notice
eligibility and explicitly supported relaunch episodes. No future-price-based
early exits, synthetic funding, zero-volume fills or silent symbol exclusion.

Known unresolved funding-source issues around June 2026 remain blockers if held.
Do not redefine the requested interval or relax checks to obtain results. Both
windows must pass all-plan preflight before the batch starts financial simulations.
Full jobs belong to the user; agent validation is small/offline or bounded source checks.

Execution acceptance: all 60 registered runs, yearly identical primary replay,
and independent source/fee/funding/NAV audits pass under existing tolerances.
Always report both candidates, all cost cases and failures. Scientific comparisons:
net return/Sharpe, MDD, costs, random-control distribution and concentration;
neither profitability nor beating BTC is a condition for honest completion.
No thresholds may be revised after observing results. Incomplete windows must
remain visibly incomplete. Provide one user-run batch command and compact summaries.
