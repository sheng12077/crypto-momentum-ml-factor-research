# User-run 2025–2026 comparison

Experiment 023, registration commit `4c52846`. Evaluate the unchanged LightGBM
ranking and equal-factor-group score together. Both portfolios retain equal
position weights, five longs/five shorts, two-week rebalancing, the same dated
universe and the same execution assumptions. No weighting or factor experiment.

| Account | Training | Trading window | Final NAV |
| --- | --- | --- | --- |
| 2025 | 2021–2024 matured labels | 2025 | 2025-12-31 00:00 UTC |
| 2026 partial | 2021–2025 matured labels | January–October 2026 | 2026-10-31 00:00 UTC |

Each account starts at 100000 USDT and fits once. These are separate annual
accounts, not continuous 2025–2026 PnL. The existing final-boundary convention
excludes the final civil day's returns. The original final-OOS dates are retained.
The partial-year calendar preserves January's two-week phase and stops in October.

## One command

From WSL:

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
conda activate funding-strategy
python scripts/run_dynamic_final_windows.py
```

The launcher runs preparation, fitting/SHAP and all-plan preflight for **both**
years before starting any financial simulations. Any failing step stops the
batch. Compatible completed stages are reused on rerun; do not delete artifacts.
Only after both preflights pass does it run and report all registered cases.
Full runtime is not measured; the 2026 training/input scope is larger than 2024.

Per year: LightGBM, equal-group and momentum60 each at 5/10/20 bps slippage,
20 fixed random controls and a primary replay: 30 cases, 60 across both years.
The original fees/no-BNB assumption and simulated funding accounting are unchanged.

For a check-only execution that does not start financial simulations:

```bash
python scripts/run_dynamic_final_windows.py --stage preflight
```

This still prepares historical inputs and fits models; it is not a quick smoke test.
After successful completion share the two compact summaries:

```bash
python scripts/run_dynamic_final_windows.py --stage summary
```

Summary mode does not fit or backtest. It prints both candidates and momentum
control at all three slippage levels. A batch success for preflight/summary only
means those requested steps passed, not that 60 financial cases completed.

## Outputs and acceptance

- Per-window log paths are printed under `reports/acquisition/dynamic_window_*.log`.
- Results: printed content-keyed paths under `data/processed/dynamic_2025/` and
  `data/processed/dynamic_2026/`.
- Launcher progress/failing step: `data/processed/dynamic_final_windows/batch_status.json`.
  This is the latest invocation's mutable status, not an immutable research result.
- Per-year `report/candidate_comparison.csv` and `report/candidate_monthly_returns.csv`.
  Equity and monthly heatmap show both candidates; all other registered results
  remain in `all_case_metrics.csv` and separate `results/<case>/` ledgers.
- English `results.ipynb`, model predictions/SHAP, source bindings and independent
  audits are preserved. Primary asset/side attribution remains the LightGBM case;
  the equal-group ledgers are separate and available for subsequent attribution.
- Each year must have `success=true`, 30 completed cases, identical primary replay
  and `independent_audit.success=true`. Report unprofitable outcomes as well.

## Data gates and verified coverage

An official delisting-index review added dated settlement assertions beyond the
earlier ledger. Configs contain 98 (2025) and 143 (2026) historical notice assertions.
The configured notice bodies, symbols/dates/publication checks were verified
with the existing public client. AERGO's evidenced 2025-04-16 relaunch is included;
both its 2025 and 2026 cessations remain represented rather than overwriting one.
Source cache bodies and hashes stay local. Official source IDs are in each config.

Examples of official references:

- [Delisting index](https://www.binance.com/en/support/announcement/list/161)
- [AERGO relaunch](https://www.binance.com/en/support/announcement/detail/82f730b7ef444a38b323ab7a2e56b757)
- [AERGO 2026 cessation](https://www.binance.com/en/support/announcement/detail/f0e3fc835b9545759e4279c64b200389)
- [October 2026 cessations](https://www.binance.com/en/support/announcement/detail/2f1a743334f044abbd82e34093c7b771)

This source review is not a certification that every possible lifecycle event is
covered. User-run preparation verifies every notice exit price before model fitting.
Unsupported events and missing required execution prices still block the run.
BTC/ETH cached spot sources have all required benchmark keys: 365 daily NAV rows
for 2025 and 304 for 2026 under the final-boundary convention.

**Known unresolved issue:** earlier source audits recorded a broad funding schedule
gap around 2026-06-24. If the new plans hold affected contracts, preflight must stop
with `funding_gap` evidence. No funding interpolation, zero-fill, future-informed
entry exclusions, or shorter evaluation period is introduced here. Supply the
printed problem-file path and compact status for a targeted source investigation.
Preparing the code does not mean the 2026 data gate has passed.

## Migration correction after the next 2025 preflight

Run `a8f57f099aeecdcb127a` stopped before PnL with six findings across BNX,
LOKA and OMNI. Their missing futures settlement facts are now included:

- [BNX: 2025-03-17 09:00 UTC](https://www.binance.com/en/support/announcement/detail/2f963977c7274e0583f16f2e26987b61)
- [LOKA: 2025-07-21 09:00 UTC](https://www.binance.com/en/support/announcement/detail/551eeaf9861c47b8ad3482f45abf3f38)
- [OMNI: 2025-09-22 09:00 UTC](https://www.binance.com/en/support/announcement/detail/13d0a79f79ef4406963dcd7f9d1de325)

BNX's 2025 ledger event was skipped by initial symbol-only registry assembly.
Both its 2023 and 2025 events are now preserved and covered by regression tests.
LOKA/OMNI migration announcements are outside the previously reviewed delisting
index subset. Their funding-tail findings occur after cessation; the correction
is the existing announced-exit rule, not invented funding. All three notice clocks
and positive-volume one-minute post-notice exit prices were verified.

A bounded saved-schedule diagnostic with the corrected public-notice eligibility
and holding-interval rules confirms none of the six old failure times remains
held. This is not a new fit, full preflight or simulation. Rerun the same batch
command: updated configs create new identities and models, source caches are
reused, and the stopped version stays preserved. Full preflight remains required.

## Memory correction after the first 2025 attempt

Run `01f451fb8c9302eab205` stopped during source preparation, before writing its
manifest or fitting a model. Kernel logs confirm OOM killed the Python process
at approximately 4.3 GiB resident memory; exit `-9` was SIGKILL, not a completed
data-preflight finding. The printed 538 symbols/48765 candidate rows include
training inputs and do not indicate concurrent positions.

The shared reader now projects only the trade close/volume/quote volume, mark
close and funding fields needed downstream. Symbol IDs share categorical codes,
monthly chunk references are released after each kind is merged, and trade
lookup uses sorted NumPy arrays with a sparse verified-repair overlay instead of
per-bar Python tuples/dictionaries. Core trade arrays occupy 32 bytes per bar;
this is not a claim about total process memory or full-run peak RAM.

All source hashes, repair checks, dated eligibility, costs and trade rules remain
in force. A stopped run stays preserved. Shared code changes create a new run
identity; existing downloaded source caches are reused, with no new dataset scope.
The same batch command resumes the work under the corrected implementation.
New `market_merge` messages identify source-merge progress. Full-history memory
peak is not yet measured; no full user job was launched during this fix.

## Current 2026 gate: collect funding evidence before another full batch

The subsequent batch passed 2025 preflight and stopped at 2026 run
`14f5d985c3030e85fb3e`: 207 findings, no PnL. The 179 internal funding-break
findings are 145 unique contracts, all on 2026-06-24. The other 28 findings are
post-cessation execution prices/funding tails across 13 contracts.

The 13 missing 2026 futures notices are now in the config; all announcement clocks
and positive-volume one-minute post-notice exit prices were verified. Existing
generic delisting articles' futures clauses referred to the aforementioned tokens,
which the earlier explicit-USDT extraction missed. Official source IDs and futures
dates are preserved in the config; spot delisting dates were not substituted.
The contracts are ATA, COS, DEGO, FIO, FUN, GHST, HIGH, NKN, OXT, STG, STORJ,
TRU and VANRY (all USDT). A saved-plan diagnostic confirms the 28 old times are
outside corrected holding intervals; new schedules still require full preflight.

**Do not rerun the complete batch yet.** Use the new read-only source investigation:

```bash
python -m crypto_factor_research funding-breaks --run-dir data/processed/dynamic_2026/14f5d985c3030e85fb3e
```

This checks all 145 saved break brackets against public fundingRate observations.
At 0.7-second request pacing, allow approximately 2–5 minutes depending on network
and cache hits. It does not prepare strategy data, fit models, compute PnL, fill
rates or alter eligibility. Progress prints every ten brackets. Evidence bodies
use the existing source cache; JSON evidence and compact summary go to a printed
content-keyed directory under `reports/tables/funding_breaks/`. Repeating the
command reuses cached source responses. Share the final summary JSON.

`success=true` means requests/validation completed, not that funding is resolved.
`api_has_additional_events` identifies potential recoverable observations for a
later explicit source reconciliation. `api_has_same_observed_gap` means the API
also has no interior record between matching anchors; it is **not** proof that
funding was zero or no payment occurred. Anchor disagreement/request failure
requires further investigation. The tool always reports financial execution
readiness as false and never modifies strategy records.

A three-contract pilot passed: all three API responses have the same observed
gap. Thus an API key is not currently an established solution. The 2025 prepared
stage/model remain reusable because this fix changes only 2026 config, CLI and
evidence tooling; no financial shared-code identity change was introduced.
The batch still requires both preflights before financial execution. No standalone
2025 financial run was launched or silently substituted for the registered batch.

## Small validation and preserved artifacts

Offline tests cover partial-year scheduling, matured labels, batch stop/order,
both-candidate report generation, repeated cessation events and independent exit
price lookup, plus earlier regression cases. Full market preparation, training,
preflight and financial runs remain the user's execution task.

Shared pipeline changes alter new run identities. To inspect already completed
2023/2024 results without creating a new run, specify their saved directory with
`window --stage summary --run-dir ...` and its original config. Example:

```bash
python -m crypto_factor_research window --config config/dynamic_2024.json --stage summary --run-dir data/processed/dynamic_2024/a51e40a2229536b092cf
```

Do not automatically rerun older windows just because their current code identity
differs. No existing dataset/result/model file was overwritten by this preparation.
