# User-run OOS comparison with adjacent-mean funding

Experiment 024, registered commit `2c38466` before implementation/performance.
The user authorized average imputation to proceed with the original OOS dates.
Only this average scenario is implemented; no parameter or portfolio-weight tuning.

## Execute

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
conda activate funding-strategy
python scripts/run_dynamic_final_windows.py --funding-assumption adjacent-mean
```

The same launcher first preflights both windows, then runs all 60 registered
cases (30/year) and reports both LightGBM and equal-factor-group candidates.

- 2025 uses its original strict config/account and existing model/prepared cache.
  Verified compatible cache at preparation: `81b2ebf6067810b2146a`.
- 2026 uses `config/dynamic_2026_mean_funding.json`, a separate account through
  October with separate artifacts under `data/processed/dynamic_2026_mean_funding/`.
- Existing raw data, strict 2026 config, stopped runs and original assumptions
  remain untouched. The strict batch remains available without the new flag.
- Complete OOS simulation/runtime has not been measured by the agent.

After completion share:

```bash
python scripts/run_dynamic_final_windows.py --funding-assumption adjacent-mean --stage summary
```

Logs are printed under `reports/acquisition/`. Progress/failure status is in
`data/processed/dynamic_final_windows_mean/batch_status.json`. Success requires
both reports, each with 30 cases, identical primary replay and independent audit.
No profit threshold is required. The two accounts are separate annual windows,
not continuous 2025–2026 compounding or a no-reset drawdown statistic.

## Exact assumption

For an internal gap, require original preceding/following observations with equal
positive reported funding intervals, finite rates and compatible nominal UTC event
times. Infer missing slots only if all fall on 2026-06-24 UTC. Allow at most 1000ms
exchange timestamp jitter when checking grid alignment. Each missing slot uses:

`estimated_rate = (original_before_rate + original_after_rate) / 2`

Multiple missing slots in one gap all use that same original-anchor mean; no
recursive interpolation. No fill of tails, other dates, uncertain interval changes,
original observations or market prices. All unrelated preflight checks remain.

The overlay is generated **after model fitting**. Original factors, labels,
training data and ranked schedules never see imputed rates. The following anchor
is future information at the estimated event time: this is a retrospective cost
assumption, not proven historical settlement or a real-time usable signal.
Cashflows affect subsequent NAV and position sizes; the engine reruns rather than
adding a correction to final returns. It is not a claim of zero look-ahead in the
assumed accounting cash path. Reported results must retain the assumption label.

## Evidence and accounting

A bounded three-day source check on the prior 2026 prepared snapshot yields
400 estimated events across 397 contracts, covering all 145 previously saved
internal-gap brackets. Only events occurring while a case holds a contract become
costs. Counts in the actual new manifest/report are authoritative for that run.

`funding.parquet` stays original. `funding_assumptions.json` records method, raw
funding hash, both source anchors/rates, interval, estimated timestamp/rate and
future-anchor disclosure. It is bound into preflight and case manifests; an
existing differing assumption file is rejected instead of silently overwritten.

The independent audit reads original funding separately, verifies adjacency,
original rates/intervals, the arithmetic mean and the complete missing-time grid,
then reconciles estimated payments, prices, fees and NAV. This verifies consistency
under the declared assumption, not that real funding payments occurred.

Reports/notebook/compact summary explicitly label the scenario. Additional
`report/estimated_funding_usage.csv` gives each case's held estimated event count
and cashflow; the summary directly includes the two candidates at 5bps. Candidate
performance CSVs and paired equity/monthly plots are retained as before.

## Reporting a completed window with a failed random control

The 2026 saved run `ff50164f4ed092093408` completed 29 cases with an identical
primary replay. Random control `random_1012` recorded a nonpositive marked NAV;
the original batch remains unsuccessful. A read-only financial reporting command
audits completed cases and discloses failed controls without assigning fabricated
full-period returns or liquidation outcomes:

```bash
python scripts/report_saved_window.py \
  --config config/dynamic_2026_mean_funding.json \
  --run-dir data/processed/dynamic_2026_mean_funding/ff50164f4ed092093408 \
  --allow-failed-random-controls
```

This command performs no preparation, fitting or simulation. Candidate failures
and replay mismatches still block reporting. `partial_report`, failure details,
the registered/completed random-control counts, and audit scope remain explicit.
The random-control distribution covers completed controls only; the full random
comparison is unavailable. Original simulation summaries and ledgers stay intact.

## Execution checks

The active dynamic engine uses exact filled-quantity deltas and a separate
fill-by-fill realized-PnL ledger. Vendor floating-point quantity remnants may be
normalized only after exact filled exposure is zero, below 0.000001 USDT, without
cash changes. The correction journal is independently audited; the existing
0.01 USDT cash/NAV reconciliation threshold is unchanged. Frozen legacy engine
bytes stay intact. This execution revision creates new content-bound run
directories; old partial outputs are retained and raw source caches reused.

Small regressions cover original-rate preservation, date/interval boundaries,
multiple missing slots, fit-before-overlay order, batch selection, a tiny actual
Nautilus case with independent funding/NAV reconciliation, rejection of a rehashed
falsified mean, and estimated-cashflow disclosure including an empty ledger.
No full preparation, model fit or historical OOS PnL was launched by the agent.
