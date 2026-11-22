# Two-week buffer sensitivity: execution handoff

## Status and scope

Experiment 011 registered at60f29cf. Implementation and preparation are complete;
the full historical candidate backtest is intentionally left for the user to run.
No candidate return is claimed in this handoff. Both2022and2023are development
years;2024and final OOS stay sealed. No model refit, new data or downloads.

Entry remains five long/five short slots. Buffer changes exit/retention criteria,
not the number of slots or the model score:

| Retention rank | Buffer width above entry5 | Existing position stays while... |
|---|---:|---|
| 5 | 0, control | in top/bottom5 |
| 6 | 1 | in top/bottom6 |
| 8 | 3 | in top/bottom8 |
| 10 | 5 | in top/bottom10 |

Boundary is inclusive: rank8 is retained by the rank8variant; rank9 exits. Fill
vacancies from entry top/bottom5. Missing current eligibility prevents retention;
fewer than20eligible =>cash/reset. Stable ties and no overlapping sides.

Membership is checked ONLY every two weeks, anchored to the year's first Monday,
with equal+/-10%NAV sizing at those decisions. No weekly exits or resizing between
them. Retained positions can still generate resizing trades on a decision date.

Four sizes x two years x5/10bps extra slippage =16cases. Four no-buffer cases reuse
the verified Experiment010C control. Twelve new Nautilus historical simulations,
plus two rank8/5bps financial replays. All source models/predictions and original
SHAP are reused; new fits=0. Fees/funding and original execution assumptions remain.

## Copyable PowerShell commands

Use the existing verified Windows runtime. The outerPython3.11launcher uses only
the standard library; it locates the isolatedPython3.13environment automatically.
No need to activate the borrowed funding-strategy conda environment. No package
installation/update or shell-policy change occurs.

```powershell
Set-Location '\\wsl.localhost\Ubuntu-24.04\home\sheng77\working_space\quant_research\strategies\momentum_strategy'
py -3.11 scripts/run_buffer_sensitivity.py --stage all
```

`all` runs/prepares/verifies cases, then creates tables/figures and executes the
English read-only notebook. Plan for a few minutes based on prior engine runs;
this exact full batch has not been timed or executed by the agent.

When complete, print the compact machine-readable summary:

```powershell
py -3.11 scripts/run_buffer_sensitivity.py --stage summary
```

Paste that JSON back for interpretation. Success requires `success:true`,
`completed_cases:16`, `verified_replays:2`, `new_model_fits:0`, and
`sealed_2024_and_final_OOS_inspected:false`. An empty supported-retention list is a
valid research outcome; it means no tested buffer passed all registered gates.

If interrupted or a process fails, re-run the SAME `--stage all` command. Completed
case checkpoints are hash-verified before reuse. Failed/partial attempts remain
under the case's `attempts/` folder. Nonzero child exit codes propagate to the
launcher, and incomplete output never becomes a successful experiment summary.
Run one instance at a time.

## Other stages and runtime choice

```powershell
py -3.11 scripts/run_buffer_sensitivity.py --stage pilot
py -3.11 scripts/run_buffer_sensitivity.py --stage prepare
py -3.11 scripts/run_buffer_sensitivity.py --stage run
py -3.11 scripts/run_buffer_sensitivity.py --stage report
```

- `pilot`: small synthetic20-asset/16-day engine accounting test; not historical PnL.
- `prepare`: verify cached models/input/schedules and create/execute the safe notebook
  scaffold, without computing candidate historical PnL. Already tested.
- `run`: execute/resume all16historical cases and two replays; no notebook rendering.
- `report`: verify complete saved results and generate tables/figures/notebook only.
- `summary`: works without the trading runtime; before completion prints
  `success:false,state:not_complete` and a completed-case count.

Pass `--python "C:/path/to/compatible/python.exe"` for explicit runtime selection.
The tested environment is underWindowsTEMP/momentum_development_005/venv.
Python3.13,Nautilus1.231.0,LightGBM4.7.0,SHAP0.54.1 and matching NumPy/Pandas from
the existing010runtime are required for comparison with cached controls.

The launcher supports a compatible existing WSL runtime via `--python` or
data/interim/runtime/nautilus313/bin/python, but does not provision it. Older WSL/
conda core package versions may be rejected. The tested copyable path above is
PowerShell/Windows; it accesses the same shared repository and data files.

## Outputs

- Logs:reports/acquisition/buffer_sensitivity_<stage>_<timestamp>.log
- Notebook:notebooks/two_week_buffer_sensitivity.ipynb (English; prepared before run)
- Executed copy:reports/acquisition/two_week_buffer_sensitivity_executed.ipynb
- Preparation:data/interim/buffer_sensitivity/v20261121_001/preparation/
- Synthetic pilot:data/interim/buffer_sensitivity/v20261121_001/pilot/
- Results:data/interim/buffer_sensitivity/v20261121_001/results/
- Final JSON:results/summary.json; all_runs.csv; paired_comparisons.csv
- Case ledgers:results/<year>/retain_<rank>/slippage_<bps>bps/
- Rank8replays:results/<year>/retain_08/primary_replay/
- Tables:reports/tables/buffer_sensitivity/
- Figures:reports/figures/buffer_sensitivity/{rank_sensitivity,equity,cost_stress}.png

No completed historical results are shipped in this work segment. The notebook
handles that state explicitly and never starts a model fit/backtest itself.

## Interpreting buffer size

Check both years, Sharpe/MDD, actual traded notional versus membership changes,
fees/funding,10bps cost stress, best-month dependence and neighboring tested ranks.
A wider buffer may keep weakening assets longer; lower membership churn does not
guarantee better performance or even monotonic actual notional reduction.

Registered supported-candidate gate, required in BOTH primary years: positive
return, Sharpe above no-buffer, MDD no worse, lower notional, and positive product
of returns outside the best month. Also require positive return at10bps in both
years. Report all passing ranks and whether adjacent tested ranks also pass. No
automatic threshold selection, finer local search or opening2024is performed.

All original caveats remain: inspected development data/multiple comparisons,
conditional retrospective cohort/identity, fractional lots, unvalidated historical
filters/liquidation and hourly VWAP/funding mark proxies. Paper/live remains false.

## Preparation checks

The agent verified rank5equivalence to the010no-buffer schedule, rank8retention
equivalence to the prior buffer primitive, thresholds/eligibility/reset/ties/phase,
checkpoint corruption rejection, launcher error/log propagation and a full report
renderer using synthetic fixtures. The actual synthetic Nautilus pilot reconciles
funding+10USDT and final cash99910USDT exactly; it checks skipped-week quantity
holding and rank6retention under an8-rank buffer. Eight schedules/26decisions each
are prepared; four safe English notebook cells execute before any historical run.
Focused isolated-runtime tests:21passed. Native regression:293passed/8optional
dependency skips. Ruff passed. The default PowerShell prepare command was tested,
and summary correctly reports zero completed historical cases before the user run.
