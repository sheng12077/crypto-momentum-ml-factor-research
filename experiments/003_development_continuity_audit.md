# Experiment 003: development input continuity audit

Registered 2026-11-21 before implementation or execution. This is a bounded
data/engineering diagnostic, not a strategy-performance or model experiment.

## Expectation

The daily development release restarts its close history on 2021-01-01. Some
symbols with existing 2020 daily data should therefore have enough numeric
warmup for January 2021 even though the old history flag is false. Quantify
this without assuming an identity/episode bridge has been proved. Also identify
the known low candidate count around 2022-08-01 from existing reason flags.

## Fixed scope and acceptance criteria

- Inspect all 924 development identifiers; a five-symbol pilot precedes full
  execution. Only load daily values from 2020-08-01 through 2022-12-31.
  Weekly decisions are the 104 Mondays in 2021–2022; features use the preceding
  day's data. No labels, forward returns, PnL, model fitting, parameter selection,
  new market downloads, or OOS performance inspection.
- Verify consumed daily files against their existing index SHA256 and bind all
  input indexes plus the early identity release. Do not modify frozen sources.
- A numeric 120-day return requires 121 consecutive calendar-day valid closes.
  Respect known development episode changes, invalid closes and partial days.
  No forward filling, missing-denominator substitution, ticker alias splicing,
  or inference of an identity bridge from a small price discontinuity.
- Joining early numeric observations is hypothetical continuity only. Preserve
  the old history/candidate flags and report additional bridge-dependent rows
  separately. If mapping evidence does not cover the full lookback through the
  feature cutoff, it must not pass the evidence-scope check. A scoped historical
  identity check is not certification of publication time, funding cashflows,
  full contract specifications, or a complete historical trading universe.
- Require seven complete days of valid aggressive imbalance inputs for its
  proposed lookback diagnostic. Funding diagnostic here is freshness only;
  do not substitute the last rate for the seven-day event-rate sum or paid carry.
- Outputs: per-symbol bridge audit, weekly data coverage, detailed 2022-08-01
  failure reasons, source bindings and a compact summary with explicit readiness
  flags. Deterministic output files must have identical hashes on replay.
- Acceptance is reproducible, fail-closed diagnostics and bounded reads, not a
  target asset count. Full historical backtest readiness remains false until
  identity/universe, execution/funding and strategy specifications are resolved.

## Stopping point

Deliver the reusable checker, pilot and full audit if runtime is modest, tests,
results and actionable next step. This audit alone must not be reported as a
historical strategy backtest or as approval of a tradable asset count.
