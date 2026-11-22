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
earlier ledger. Configs contain 95 (2025) and 127 (2026) historical notice assertions.
The 127 configured notice bodies, symbols/dates/publication checks were verified
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
