# User-run 2023 window

Train2021–2022;simulate2023. Strategy/features/model parameters/two-week5long/5short
weights,costs and30registered financial executions match Experiment020. New dated
cessation facts and episode-specific reentry follow Experiment021. This is retrospective
research,not a new untouched OOS. Agent preparation used ten synthetic tests and lint;
no historical2023data preparation,fitting,downloads or simulation were executed.

From WSL:

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
conda activate funding-strategy
python -m crypto_factor_research window --config config/dynamic_2023.json --stage all
```

The user-triggered command performs source verification/bounded recovery,2021–2022
matured-label training,TreeSHAP,all-plan preflight,Nautilus simulations and reporting.
It stops on preflight blockers and saves all problems before financial runs. Public
source requests require no API key. Completed compatible stages/cases are reused.
Full2023runtime has not been measured;no short-runtime promise is made.

The command prints its log path under reports/acquisition and its content-keyed
result directory under data/processed/dynamic_2023/. Success requires success=true,
registered_cases_completed=30,primary_replay_identical=true and an independent audit.
Results include English results.ipynb,monthly/equity PNGs,all_case_metrics.csv,
asset/side attribution and SHAP tables. Recovered sources and failures remain auditable.

After completion,share only this compact output:

```bash
python -m crypto_factor_research window --config config/dynamic_2023.json --stage summary
```

If a source/price/terminal issue remains,share the compact summary and the printed
problem-file location;do not edit prices,zero-fill funding or drop entire identifiers.
Current metadata/vintage,bar execution and historical filter assumptions remain
conditional research limits;code preparation alone is not data or execution certification.

The completed2022artifacts stay unchanged at
data/processed/dynamic_first_window/57a76d3c3a17b445f1b1/.
Annual code generalization changes new run fingerprints. To read the saved2022summary
without retraining or rerunning:

```bash
python -m crypto_factor_research window --config config/dynamic_first_window.json --stage summary --run-dir data/processed/dynamic_first_window/57a76d3c3a17b445f1b1
```

`window`is the common configured entry;`first-window`is a compatibility alias to the
same implementation. No duplicate backtester or new weighting/buffer experiment.
