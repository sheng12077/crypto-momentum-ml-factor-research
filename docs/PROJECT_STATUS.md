# Project status

## Current state -- 2026-11-22

- User requests local architecture cleanup only; no GitHub repository/remote or push.
- Work branch chore/package-research-pipeline from exp/final-holdout-2025-2026.
  When complete, merge tooling into that parent and delete the topic; inspect latest
  merge for exact commit. Parent remains off main while older control blockers remain.
- Core lives in src/momentum_data/{data,features,models,portfolio,backtest,reporting}.
  scripts/ now contains3thin launchers. config/continuous.json names the frozen run;
  local root overrides are MOMENTUM_PROJECT_ROOT/MOMENTUM_DATA_ROOT.
- Previous scripts/tests/config/notebooks/docs and frozen source/protocol copies
  live in research/legacy. The package never imports legacy scripts. Original source
  bytes and logical contracts are preserved; original data/output untouched. Local
  ignored legacy/data and legacy/reports aliases preserve historical compatibility.
- Original working edits moved with their files and were not staged. All19original
  status paths have unchanged index blobs;17substantive diffs remain under legacy.
  Do not stage, discard or normalize these user modifications.

## Verification and conclusions

- Editable install and combined354tests+31subtests passed. CLI help and
  synthetic accounting work from /tmp. Active undefined-name checks/compilation pass.
- Full cached-data preflight:5models,127rebalances,243851events, same schedule.
- Actual new-engine5bps/10bps/primary replay all match original financial SHA256
  exactly, with independent every-fill/fee/pre-fill Funding audits.0newfits/downloads.
- Current English notebook executed successfully; ignored output reports/acquisition/
  package_results_notebook_executed.ipynb. Public doc links resolve.
- docs/PACKAGE_MIGRATION_VERIFICATION.md records financial hashes and check limits.
  Source/output contract data/interim/continuous_package/v20261122_002/.
- Strategy conclusions unchanged:full-period+84.06%,Sharpe.645,MDD-26.77%;stress
  +67.56%.2024onward+8.09%,Sharpe.238.28/58positive months,median-.11%,worst
  2026Oct-20.33%. Retrospective37-asset cohort, not fresh OOS/live-readiness proof.
- Momentum-only EOSterminal settlement remains unverified; no fabricated baseline.

## Commands and next task

```bash
conda activate funding-strategy
python -m momentum_data smoke
python -m pytest tests -q
python -m momentum_data verify
python -m momentum_data replay
python -m momentum_data summary
python -m momentum_data publish
```

README, docs/PROJECT_STRUCTURE.md and the migration verification explain supported
paths and installation. Original entry commands remain thin compatibility wrappers.
No user backtest rerun is needed to validate this migration; completed exact replays
already exist. Review the reorganized local project. Do not push unless a future
user request specifies a repository and authorizes publication.

Detailed pre-migration handoff history is preserved in
research/legacy/docs/PROJECT_STATUS.md. Registration016:a808b5e; original simulator
3182f37/merge13785db; results publication596517f/merge47ec8af.
