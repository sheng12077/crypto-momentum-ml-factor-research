# Weekly baseline temporal contract and development coverage

Preregistered on main at `ee792fa` before implementation:
[Experiment 001 stage 0](../experiments/001_weekly_baseline_stage0.md).
Configuration: `config/weekly_baseline_v1.json`.
Tools: `scripts/weekly_contract.py`, `scripts/check_weekly_baseline.py`.

This stage fixes timing and checks coverage, not profitability. No prices,
returns or targets are materialized, no model fitted, and no final OOS rows
materialized. Whole source files are hashed for integrity, including their
bytes outside development; this is not OOS performance inspection. Projected
columns are instrument/day/reference and four boolean candidate flags, filtered
to reference times strictly before2025-01-01 UTC.

## Fixed research clock

| Event | UTC time |
| --- | --- |
| Feature cutoff | Monday00:00, preceding Sunday data day |
| Decision | Monday01:00 |
| Entry proxy | Complete Monday01:00--02:00 hourly VWAP |
| Exit proxy | Next Monday01:00--02:00 hourly VWAP |
| Earliest assumed label availability | Next Monday03:00 |

VWAP means total quote volume / total base volume in that hour, unknown at
decision time. The later label is exit proxy / entry proxy minus one, before
costs/funding. Publication lags and execution at VWAP are explicit unverified
assumptions. Stage0 computes no label values and claims no actual fill. Fees,
slippage, funding cashflows and terminal accounting still precede funded PnL.

A label is permitted only if its assumed availability is strictly before the
applicable end boundary. Calendar purge rows remain explicit. Price/episode
validity may exclude further rows;initial feature warm-up is not waived.

| Period | Calendar rows | Time-only usable | Boundary purge |
| --- | ---: | ---: | ---: |
| Round1 training2021--2022 | 104 | 103 | 1 |
| Round1 validation2023 | 52 | 51 | 1 |
| Round2 training2021--2023 | 156 | 155 | 1 |
| Round2 validation2024 | 53 | 52 | 1 |

209 unique decisions span2021-01-04 through2024-12-30. These are time
permissions, not209 valid return samples per asset.

## Completed checks

- All121 regression tests pass, including10 new tests covering boundary purging,
  horizon/clock,timezones,OOS guards,projection,missing/duplicate weekly rows,
  corruption and checkpoint reuse. Changed files pass Ruff lint/format.
  Native Python3.11/Arrow11 tested;configured runtime3.13.
- Real BTC/BNX/SUN pilot passed15.422s;verified resume13.125s/3 hits.
  All924 source indices are bound even for the pilot. Pilot assumed-Size weekly
  counts:min0,median1,max2;do not extrapolate to the full universe.
- Full924-name weekly coverage NOT run. Runtime unknown;pilot timing includes
  shared metadata verification and is not a linear full-run estimate.

## Full development coverage in WSL

From the repository:

```bash
conda activate funding-strategy
python scripts/check_weekly_baseline.py full
python scripts/check_weekly_baseline.py summary
```

No downloads or new packages beyond the working data-build environment. Run
only one writer/host. Rerun the same command after interruption with unchanged
inputs/code;checkpoints are revalidated.

Log: `reports/acquisition/weekly_baseline_full_20261118.log`.
Output: `data/interim/weekly_baseline_stage0_20261118/full/`:

- `calendar.json`: timing and split permissions,no label values.
- `weekly_counts.json`: four candidate counts per decision date.
- `coverage_by_year.json`: min/median/max and fraction with at least20 assumed-
  Size candidates,including2021 warm-up instead of discarding it.
- `instruments/`: per-name checkpoints;`summary.json`: compact run status.

Expected full summary:success=true,errors=[],full_scope=true,identifiers=924,
weekly_decisions=209;model_fitted,label_values_computed,PnL_computed and
OOS_performance_inspected allfalse.

20 names is a fixed diversification diagnostic,not a holding-count decision or
profitability gate. Strict eligibility/Size-vintage flags remainfalse by design.
Ex-post input qualification does not certify a causal historical tradable pool.

After coverage,specify holdings/exposures,predictors,model baselines/challenger,
refit,costs,funding/settlement and economic/statistical thresholds before
performance implementation. Buffer/sizing remain later;OOS stays sealed.
