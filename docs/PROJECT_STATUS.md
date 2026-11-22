# Project status

## Prepared main publication -- 2026-11-22

- User reports GitHub shows old README; confirmed main=a808b5e while research
  branch1e99966contained16new commits. User authorized local publication preparation.
- Remote now exists:origin=https://github.com/sheng12077/crypto-momentum-ml-factor-research.git.
  Latest read required GitHub login. No push, force push or history rewrite performed.
- Topic docs/prepare-main-publication adds publication scope/check record; merge the
  completed research package into local main with no-ff, then remove completed branches.
  Unlike prior interim notes, known control limits are now explicitly closed as a
  documented partial research outcome for publication, not a claim all cases passed.
- Original015flags remain success=false/data_complete=false:8valid cases,4blocked
  EOSmomentum controls. No criteria revised and no fabricated control/settlement.
- Exported committed1e99966tree into isolated snapshot:356tests+31subtests pass
  without user edits/local data.483Git blobs scanned; no checked credential patterns
  or market-data history paths found. Public documentation links checked.
- Engine/model/data code matches verified003; later changes only publication/badge
  and output namespace004. No new backtest necessary for this Markdown-only step.
- Back up and restore existing19original working files byte-for-byte around main
  checkout; keep substantive legacy edits unstaged. Release contains committed tree.
- Next: after local main is ready, obtain required push confirmation and GitHub
  authentication, recheck remote and push only main. Never put credentials in chat.


## Added truthful README badges -- 2026-11-22

- Topic docs/readme-project-badges from current experiment; merge back when complete.
- README badges:Python3.13,NautilusTrader,locally verified checks,retrospective research.
  Each links to implementation/verification evidence. No unconfigured CI, coverage,
  license, profitability or live-trading claims. Publisher retains badges on regeneration.
- Presentation-only change; no model/engine/accounting source changed. No new tests or
  historical simulations needed. Existing package003exact replay evidence remains valid
  for that recorded source version. Namespace004reserved for future source-bound replay;
  no old contract or financial result overwritten. No remote/push.


## Full-period / original OOS disclosure -- 2026-11-22

- User requests explicit separation of full-period and OOS results. Presentation only;
  no signal, model, decision calendar, fee or label changes. No remote/push authorized.
- Work topic docs/separate-full-period-and-oos from425f6d5; merge into existing
  exp/final-holdout-2025-2026 when complete. Preserve all legacy working edits.
- README/results now distinguish2022--23development,2024frozen validation,
  original2025--Oct2026final OOS(now disclosed), and post-disclosure full reconstruction.
- Full primary:+84.06%,CAGR13.45%,Sharpe.645,MDD-26.77%. Original independent OOS
  account:+16.31%,CAGR8.61%,Sharpe.435,MDD-24.79%; OOS10bps+12.25%.
- Do not replace OOS with full-account same-date slice:+24.08%,Sharpe.557, inherited
  2024positions. Both slices startJan1 2025 00UTC/endOct31 2026 00UTC but different
  starting accounts. OOSannual fits remain original allowed expanding-window policy.
- Original OOS code/registration/runtime/run/case hashes verified. Daily NAV metrics
  recomputed and match saved OOSmetrics. Known momentum-only EOScontrol stays blocked.
- docs/assets/full_period_vs_oos.png shows separate account equity; full monthly
  heatmap has a phase divider and explicit carry-in labels. Original OOSmonthly
  table and matched spot benchmarks are separately reported in detailed results.
- Active9tests passed, including independent OOS-vs-carry attribution and date-grid
  rejection. Publication is idempotent; links/source hashes checked; figures viewed.
- Prior verified package002remains immutable. Publication changes use package003
  output provenance. All three package003financial hashes matched original frozen
  cases; verification.json confirms equality. No new fit/download or rule change.
- Next: review the new disclosure; no fresh OOS exists in these already seen dates.


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
