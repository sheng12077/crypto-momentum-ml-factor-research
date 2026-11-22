# User-run 2024 validation

Experiment 022: train 2021–2023 with labels available before 2024; simulate 2024.
Unchanged dynamic universe, model/features, two-week five-long/five-short equal
weights, fees, 5/10/20 bps slippage, 20 random controls and replay. Total: 30 cases.
2024 is a validation window; 2025–2026 remains the original final-OOS interval.
Previously disclosed prototype results mean neither interval is fresh untouched OOS.
The final NAV remains December 31 at 00:00 UTC, excluding the final civil day.

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
conda activate funding-strategy
python -m crypto_factor_research window --config config/dynamic_2024.json --stage all
```

This user-triggered command verifies sources, performs bounded public recovery,
prepares data, fits the new model and computes TreeSHAP, checks all registered
plans before simulation, runs Nautilus, and produces the independently audited
report. No API key is needed. Full runtime is not measured. Compatible completed
stages/cases are reused; rerun the same command after resolving a blocker.

Log: printed path under `reports/acquisition/`. Results: printed content-keyed
directory under `data/processed/dynamic_2024/`. Includes English `results.ipynb`,
equity/monthly plots, all-case metrics, SHAP and asset/side attribution.

Success requires `success=true`, `registered_cases_completed=30`,
`primary_replay_identical=true` and `independent_audit.success=true`. These certify
execution/accounting checks, not profitability or live trading readiness.

After completion, share this compact output:

```bash
python -m crypto_factor_research window --config config/dynamic_2024.json --stage summary
```

Missing required prices or unsupported held cessation events block the run and
are saved in problem files. Do not zero-fill costs or drop entire identifiers.
Preparation alone does not certify all required prices; the full preflight is
part of the user-run command. Existing 2022/2023 artifacts stay unchanged.

## Lifecycle source coverage

The config inherits prior notices and adds the local registered 2024 settlement
ledger. Additional migration and May cessation references were checked against
official announcements; the pipeline verifies their bodies and post-notice exit
prices when the user runs it. Historical publication-vintage limits remain.

- [STRAX migration](https://www.binance.com/en/support/announcement/detail/2e6eb8e644664a6ca7b6659a226c41b0)
- [RNDR migration](https://www.binance.com/en/support/announcement/detail/d1f2ae8d99b24439a7a900caa9bb6b3b)
- [MATIC migration](https://www.binance.com/en/support/announcement/detail/6a6de383727f4659a3050f7982e1620f)
- [STPT/SNT/MBL/RAD/CVX cessation](https://www.binance.com/en/support/announcement/detail/a58cc13f78a34fbba11f00ff7144e9ee)
