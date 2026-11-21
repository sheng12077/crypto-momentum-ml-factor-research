# Frozen 2024 validation: user-run handoff

Preregistration: `experiments/013_frozen_2024_validation.md`, commit `0f07723`.
The candidate is fixed: original five-input LightGBM, expanding 2021--2023 training,
seven-day labels strictly available before 2024; two-week first-Monday phase,
equal-weight five long/five short, no buffer. Primary extra slippage 5 bps, stress
10 bps, plus 5 bps taker fees without BNB. BTC/ETH benchmarks use spot prices.
Final 2025--October 2026 performance remains sealed.

## Execute in WSL

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
conda activate funding-strategy
python scripts/run_frozen_2024.py --stage all
python scripts/run_frozen_2024.py --stage summary
```

If Conda activation is unavailable, substitute
`/home/sheng77/miniforge3/envs/funding-strategy/bin/python` for `python`.
Expect a few minutes with existing caches, depending on machine/network load.
No keys or new packages are required in the already validated environment.

The runner logs to `reports/acquisition/frozen_2024_<stage>_<UTC>.log`. Individual
stages are `prepare`, `spot`, `simulate`, `report`; `all` executes them in order.
Verified existing inputs/models/completed cases in the same output version are reused. Never delete a
contract to bypass a code/runtime/source mismatch; report the error instead.
Run one instance at a time.

## Current progress and execution disclosure

The agent prepared 2024 inputs (1932 scored-feature candidates; 1887 matured 2023
training labels added), with no futures source repairs, and verified 24 BTC/ETH
spot monthly archives. Synthetic calendar, strict purge, future-invariance and
unchanged scheduling checks passed (13 tests).

The historical command had already started when the user requested execution
handoff. It was stopped promptly via SIGTERM. Completion markers exist for the
model, ML 5/10 bps, momentum 5 bps and primary ML replay. Full summary/report is
absent. These are partial artifacts, not a completed or interpreted experiment.
They remain intact under version v20261121_001, with exact interrupted source
bytes archived in `interrupted_code/`. The deliverable uses v20261121_002 with LF
source bytes matching Git; the user command performs a clean four-case run there.
Trading rules are unchanged. Verified 2024 spot archives from v001 are reused.
No candidate rules were changed after execution started. Final OOS was not opened.

## Success criteria and outputs

Require exit code zero, 4 registered cases, identical primary replay, independent
verification, no final holdout inspection and four successfully executed report
notebook code cells. A performance gate being false is a valid scientific result,
not an execution failure. All three evidence gates were registered before opening
2024; do not change them after viewing performance.

- Full JSON: `data/interim/validation_2024/v20261121_002/results/summary.json`.
- Verification: same folder, `independent_verification.json`.
- Tables: `reports/tables/validation_2024/`.
- Figures: `reports/figures/validation_2024/`.
- English notebook: `notebooks/validation_2024_results.ipynb` (prepared unexecuted).
- Executed notebook: `reports/acquisition/validation_2024_results_executed.ipynb`.

Send the compact `--stage summary` JSON for interpretation after execution. The
last NAV is 2024-12-31 00 UTC, after forced close Dec30 23 UTC: 366 NAV snapshots,
365 daily returns. Do not describe this as full Jan1-to-next-Jan1 performance.
Historical universe membership, hourly VWAP fills, funding proxies, fractional
lots and unvalidated liquidation remain material limits on live applicability.
