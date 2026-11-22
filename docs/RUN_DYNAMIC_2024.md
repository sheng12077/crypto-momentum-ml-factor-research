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

### Preflight correction: six missing notices

Run `e58811244cbeac121539` stopped before PnL with 12 execution-price failures
across six unique contracts. Public recovery returned zero-volume flat bars,
not executable liquidity. Their cessation notices were missing from the config:

| Contract | Futures cessation (UTC) | Official source |
| --- | --- | --- |
| GALUSDT | 2024-07-11 09:00 | [GAL migration](https://www.binance.com/en/support/announcement/detail/27449abd481b473493b9c058350b4e2e) |
| KLAYUSDT | 2024-10-22 09:00 | [KLAY migration](https://www.binance.com/en/support/announcement/detail/f75f933759ee49d0af1dfbce7e32144c) |
| UNFIUSDT | 2024-10-30 09:00 | [UNFI cessation](https://www.binance.com/en/support/announcement/detail/043c8407bb904652a428573a50d07e07) |
| BONDUSDT | 2024-12-16 09:00 | [BOND cessation](https://www.binance.com/en/support/announcement/detail/27eac260521b4f40ab331e1a345887a7) |
| BLZUSDT | 2024-12-23 09:00 | [BLZ cessation](https://www.binance.com/en/support/announcement/detail/b140faee7cf9482cb10257308abda245) |
| DARUSDT | 2024-12-26 09:00 | [DAR migration](https://www.binance.com/en/support/announcement/detail/21551cde98784f64b374f8d50ff2a438) |

All six notice bodies/publication timestamps and positive-volume one-minute
post-notice exit bars were verified using the existing public-source client.
The existing five-minute notice handling rule is unchanged. No zero-volume bar
is treated as a fill. Contracts retain their pre-announcement eligibility.

Rerun the same `--stage all` command. The corrected config creates a distinct run
directory and refits the model because notice filtering changes training inputs
and trading candidates. The stopped run stays preserved; it is not a valid result.
No strategy PnL was computed during this correction. Full plan preflight must
still pass on the new schedules before financial simulations begin.
