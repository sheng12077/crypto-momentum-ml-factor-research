# Project status

## User-authorized average-funding OOS scenario prepared — 2026-11-23

- Experiment024 registration2c38466 precedes implementation; topic
  feat/mean-funding-oos. User explicitly authorized adjacent average to see OOS.
- Read docs/RUN_MEAN_FUNDING_OOS.md. Run:
  python scripts/run_dynamic_final_windows.py --funding-assumption adjacent-mean
  Same flag with --stage summary after completion. Strict default retained.
- 2025 strict config/model cache81b2ebf6067810b2146a verified compatible/passed.
  New2026 config dynamic_2026_mean_funding.json/output dynamic_2026_mean_funding.
  Shared original financial identity code unchanged; no unnecessary 2025 refit.
- New mean_funding_window orchestrates existing engine: fit on original data,
  then accounting-only adjacent mean for stable-interval Jun24 internal slots.
  Raw funding stays unchanged; source-bound funding_assumptions.json separate.
- Bounded source recipe check:400 nominal events/397 contracts, covering145/145
  known brackets. Not a full new preflight or proof of actual settlements.
- Independent audit reconstructs assumed rates/times from original adjacent rows
  before checking funding/NAV. Future-anchor use and paid-estimate usage appear
  in report, notebook, summary and estimated_funding_usage.csv. Not a live signal.
- 51 targeted tests/lint and launcher help pass, including tiny actual Nautilus
  mean-funding payments and independent audit. Full historical runs belong to user;
  no full prepare/fit/OOS simulation launched by agent.
- Preserve all unrelated data gates; no tails/other-day filling or additional
  scenarios. Both yearly preflights still required. User legacy edits untouched.

## Alternative funding sources investigated — 2026-11-23

- User completed c946056e6180c28e76cb evidence audit: all145 REST brackets have
  same observed gap; no new funding records, no resolution of payable costs.
- Read docs/ALTERNATE_FUNDING_SOURCES.md. Supplied Postman calls the same fapi
  endpoint. Binance website POST history was separately paginated for VVVUSDT:
  Jun24 00→08 UTC, missing04, anchors still say4h; four source pages preserved
  under data/repairs/funding_website_probes_20261123. No strategy mutation/PnL.
- Amberdata documents applied-vs-predicted rates but requires authorized access;
  sample not obtained. Tardis metadata includes VVV and independent live-feed
  recording; actual June24 data not accessed. CoinGlass OHLC close is predicted,
  not settled. Coin Metrics community probe did not provide VVV records.
- No verified replacement or specific official June24 exception found. Next:
  user may request one applied-rate/live-feed sample before paying; request text
  in source note. Do not silently waive the gate or buy data without confirmation.
- Documentation-only research segment; no external messages sent. User legacy
  edits preserved; no push/history rewrite.

## 2026 source gate: lifecycle corrected, funding still unresolved — 2026-11-23

- Topic fix/2026-preflight-evidence. Latest batch passes 2025 preflight; 2026
  run 14f5d985c3030e85fb3e fails with 207 findings, no PnL.
- 179 internal funding-break findings = 145 unique contracts, all Jun24 2026.
  Other 28 findings concern 13 post-cessation contracts. Added their official
  futures dates; source clauses used generic token references missed by earlier
  explicit-USDT extraction. 2026 config now143 assertions, 2025 unchanged98.
- Verified all13 official notices and positive one-minute announcement exit bars.
  Saved-plan diagnostic confirms all28 old times fall outside corrected holds.
  No full reprepare/fit/preflight/backtest executed; new schedules remain unchecked.
- New CLI funding-breaks --run-dir data/processed/dynamic_2026/14f5d985c3030e85fb3e
  audits only saved brackets/public funding records, no strategy mutations/PnL.
  User runs full145 source checks; output reports/tables/funding_breaks/<hash>/.
- Three-contract pilot299b27869d2e009cf5e4: all3 matching API anchors but same
  missing interior records. Absence does NOT establish zero costs/no settlement.
  43 targeted tests and changed-file lint pass. Financial readiness remains false.
- Do not rerun full batch yet; collect source evidence first. 2025 caches remain
  identity-compatible. Original both-year preflight gate is retained; no alternative
  2025 standalone run or scientific rule change made without user direction.
- User legacy changes preserved. No push/history rewrite.

## 2025 migration blockers corrected — 2026-11-23

- Topic fix/2025-migration-notices. User run a8f57f099aeecdcb127a reached
  preflight after memory fix; six findings concern BNX/LOKA/OMNI, no PnL.
- Added 2025 futures settlements BNX Mar17, LOKA Jul21, OMNI Sep22 at 09UTC
  to both final-window configs. BNX 2025 had been skipped by initial symbol-only
  registry assembly; preserve both 2023/2025 events. LOKA/OMNI funding-tail flags
  follow cessation, addressed by announced exits, not fabricated funding rows.
- Verified three official source bodies/clocks and positive-volume one-minute
  post-notice exits. Saved-plan diagnostic: all six old timestamps fall outside
  corrected holding intervals. No full prepare/fit/preflight/simulation launched.
- 34 targeted tests/lint pass. Config assertion counts now 98/130 for 2025/2026.
- User reruns python scripts/run_dynamic_final_windows.py; config changes require
  new identities and models, source caches remain reusable. Full preflight still
  required; known June2026 funding issue unchanged. User legacy edits preserved.

## Confirmed OOM corrected in annual window preparation — 2026-11-23

- Topic fix/window-memory-usage; no strategy/config/date/cost changes.
- 2025 run 01f451fb8c9302eab205: 538 symbols/48765 candidate rows, then SIGKILL
  (-9). Kernel OOM log confirms Python PID 24594 killed with 4541736 KiB anon RSS.
  Only source_errors.json exists: no prepared manifest, model or preflight result.
- Projected unused market columns out, categorical symbol IDs shared across
  monthly chunks, release chunk collections after merging, compact NumPy trade
  lookups plus sparse repair overlay. Preserve all source/hash/conflict/zero-volume
  checks. Trade arrays 32 bytes/bar; full process peak remains unmeasured.
- 32 targeted tests and changed-file lint pass, including actual tiny Nautilus
  accounting cases and nonempty recovery overlay. No full data job/fit/backtest.
- User reruns python scripts/run_dynamic_final_windows.py; source cache reused,
  new content-bound run directory. Do not rerun the known old failed identity.
- Existing 17 user legacy edits untouched. No push/history rewrite.

## Dual-candidate 2025–2026 preparation completed — 2026-11-23

- Experiment 023 registration 4c52846 preceded implementation. Completed topic
  feat/dynamic-final-windows; merge with no-ff. No push/history rewrite.
- Read docs/RUN_DYNAMIC_FINAL_WINDOWS.md. New configs dynamic_2025/2026.json;
  annual expanding fits, separate 100000-USDT accounts, unchanged ranking/position
  rules/costs. 2026 stops at October boundary; no continuous-account claim.
- User command: python scripts/run_dynamic_final_windows.py
  Both years must pass preflight before any financial simulation. 30 cases/year,
  60 total; LightGBM and equal-group candidate results directly visible in compact
  summaries, comparison CSV, equity plot and paired monthly heatmap.
- Added partial-year schedule bound and repeat-cessation support, including
  independently checked exit-price lookup. AERGO 2025 relaunch is source-bound;
  its two cessations no longer overwrite one another.
- Official index/source review: 95 notice assertions for 2025, 127 for 2026.
  All 127 source identity/date/publication checks pass; new launch source checked.
  Cached BTC/ETH required spot keys pass (365/304 daily NAV rows). This does not
  certify every lifecycle event or all notice exit bars; user-run prepare checks those.
- 27 targeted synthetic/CSV-fixture/regression tests and changed-file lint pass;
  launcher help smoke passes. No full market prepare, model fit, preflight, PnL
  or final-period performance inspection by agent during this preparation.
- Known June 2026 funding gaps may block held schedules; never zero-fill or silently
  omit affected assets/intervals. Log paths and batch_status.json locate failures.
- Shared code changes new identities; read old 2024 results using explicit --run-dir
  a51e40a2229536b092cf and original config; do not rerun older windows automatically.
- Existing 17 user legacy edits preserved. Next: user execution, then summary.

## Completed 2024 result attribution — 2026-11-22

- Run a51e40a2229536b092cf: 30 cases, replay and independent audit passed.
- Read docs/DYNAMIC_2024_ANALYSIS.md. Model 5bps -7.19%, Sharpe -0.006,
  MDD -37.75%; matched equal-group score +116.62%, 1.941, -31.23%.
- Equal-group score is not position weighting: both cases hold equal weights.
  Model long +23207.84 / short -30401.97 USDT; all three 5bps cases' side-ledger
  sums reconciled within 0.01. No new backtest or fit, only existing CSV reads.
- Model excluding best month -23.30%; equal-group +67.38%. Model still loses
  before fees/funding at existing slipped fills; fee reduction alone is insufficient.
- Next research decision remains with user; no weighting/new-factor/OOS execution
  launched. Preserve candidates separately; do not select/tune silently on 2024.
- Completed on research/2024-result-attribution; no-ff merge. User edits preserved.

## 2024 missing cessation facts corrected — 2026-11-22

- Topic fix/2024-cessation-coverage; corrected config and run documentation.
- Stopped run e58811244cbeac121539: 12 execution VWAP failures, six unique
  contracts (UNFI/BOND/KLAY/GAL/BLZ/DAR). Six recovered bars had zero volume;
  missing cessation notices caused invalid post-cessation plans. No PnL computed.
- Added six official source/date assertions, verified all six notice bodies,
  publication clocks and positive-volume one-minute post-notice exit prices.
  Existing five-minute exit/filter logic and model parameters unchanged.
- Same command creates a new content-bound run and refits because candidate and
  training filters change. Preserve stopped artifacts; do not reuse its model.
- Thirteen small regression tests/lint pass. No full prepare, fit, preflight or
  simulation launched. User runs config/dynamic_2024.json --stage all then summary.
- Existing 17 user legacy edits untouched; no push/history rewrite.

## 2024 user-run preparation completed — 2026-11-22

- Experiment 022 registration 6a16769 committed on main before implementation;
  topic feat/user-run-window-2024 completed and merged with no-ff.
- config/dynamic_2024.json and docs/RUN_DYNAMIC_2024.md use the same window CLI.
  Train 2021–2023 / trade 2024; unchanged features/model/two-week 5L5S/costs and
  30 cases. 2024 is validation, 2025–2026 the originally assigned final OOS;
  earlier prototype disclosure prevents fresh-untouched-OOS claims.
- Added 2024 locally registered settlements plus official STRAX/RNDR/MATIC and
  STPT/SNT/MBL/RAD/CVX notices. User-run preparation verifies bodies/exit bars;
  full preflight remains required. No assertion of complete execution readiness.
- Thirteen targeted tests and changed-file lint pass; both cached 2024 spot
  benchmarks have all required prices (366 daily rows). No strategy historical
  preparation, fitting, full preflight or backtest launched by agent.
- User command: python -m crypto_factor_research window --config config/dynamic_2024.json --stage all
  Then share --stage summary. Logs under reports/acquisition; results under
  data/processed/dynamic_2024. Full runtime not measured. No 2025–2026 PnL inspected.
- Existing 17 user legacy edits untouched; no push or history rewrite.

## 2023 benchmark preflight fix — 2026-11-22

- Topic fix/spot-benchmark-required-keys; completed fix merged with no-ff.
- Run e199229092439e24d200 stopped only on BTC/ETH spot calendar checks.
  Both verified archives omit the same unused hourly bar (1679662800000).
  Every required execution and daily valuation price is present.
- Benchmark validation now requires the exact execution/valuation timestamps;
  missing required prices still fail. Source checksums, identity, timestamp grid
  and source-month bounds are checked. No filling or fabricated prices.
- Ten targeted tests and changed-file lint pass; both cached 2023 benchmarks
  produce 365 daily rows. No full preflight, training or simulation launched.
- Only reporting validation changed: existing prepared data/model identity remains
  reusable. User resumes with the same window --config config/dynamic_2023.json
  --stage all command. Existing 17 legacy edits untouched; no push.

## 2023 user-run preparation completed — 2026-11-22

- Experiment021registration2917c70;topicfeat/user-run-window-2023,merge completed
  preparation to main with no-ff. Full2023execution belongs to user;do not launch it.
- config/dynamic_2023.json and docs/RUN_DYNAMIC_2023.md give one shared windowCLI.
  Train2021–2022/trade2023;unchanged model/features/two-week5L5S/equal weights/costs.
- Date ranges,schedules,spotcalendar,reportlabels and registration bindings generalized;
  prior cessation applies only to its episode. Saved2022artifacts are untouched and
  readable with --run-dir. New2023model/run uses a distinct content identifier.
- Added known2023BNX/HNT/COCOS/TOMOofficial notice references;user-triggered prepare
  verifies public source bodies and exit prices. No claim those requests have passed yet.
- Ten targeted synthetic tests and changed-file lint pass;CLI help smoke test passes.
  No historical2023prepare,fit,PnL or downloads. No conclusions or extra tuning added.
- User command:python -m crypto_factor_research window --config config/dynamic_2023.json --stage all
  After completion request only --stage summary output. Logs/results paths printed.
- Old17userdirtylegacyfiles untouched. No push or history rewrite.



## First-window implementation preserved; 2023 preparation next

- Experiment020 registration1553967; completed first-window code on exp/dynamic-first-window.
- Results:data/processed/dynamic_first_window/57a76d3c3a17b445f1b1;30cases and replay passed,independent audit passed.
- 2021train/2022simulation;conclusions deferred by user. Original artifacts remain frozen.
- User requires full training/backtests to be run personally:prepare code,small tests and one CLI command only.
- Existing17dirtylegacyfiles untouched. No push/history rewrite.



## Dated pool-capacity diagnostic completed — 2026-11-22

- Completed topic research/dynamic-universe-capacity;main after no-ff merge.
  Experiment019registration24c10d8predates implementation/count inspection.
- Read docs/DYNAMIC_UNIVERSE_CAPACITY.md. All924IDs x304Mondays accounted.
  Newcapacity.py plus capacity-auditCLI;no model/PnL,new downloads or source overwrite.
- Finalignoredartifact:reports/tables/dynamic_universe_capacity/bdd1832d201a3a81105e/.
  Broad dated candidate yearlymin/median/max:2022 80/120/135;2023 134/159.5/196;
  2024 196/241/263;2025 267/351.5/448;2026 127/500/511.2021includes0warmup.
  Both broad/current-COIN-supported comparisons exceed100everyweek since2023.
  Current metadata is conditional retrospective scope evidence,not certified PIT.
- Preserve unknown historical class/currently absent identifiers and pre-onboard
  prior episodes. No whole-symbol survival gate,no top-N/liquidity filter.
  Original funding-duration and phase flags unchanged;repair overlaynotintegrated.
- Fullbuild+boundsource/output verifiedcache reuse pass;39active tests+lint pass.
  Allcandidate prior-day mark snapshots available in verified source union;not
  certification of required decision/fill/held/terminal marks.
- Knownbounded samefrequency funding observation breaks:385nominalslots,allJune24.
  14dayhypothetical holding flags:June15 372/500candidates;June22 374/502.
  Future flags never alter entry mask;these are potential candidates,not held positions.
  ExcludingJune29newentrydoesnotrepairunknownJune24cost for existing positions.
- An initialunpublisheddiagnostic incorrectlybridgedsparsecheckedmonths;marked
  INVALIDATED.md in18a81606bc8a2ab02bf2. Finalcodechecksbreaksperboundedjob;
  regressiontestpreventsrecurrence. Neveruseinvalidatedholdingcounts.
- Execution_ready=false. Next:dated-ruledefinition/acceptedoverlayintegration and
  actualheld/targetexecution/cost/terminalpreflight;no needforceeveryassetalwaysvalid.
- Existinguserlegacyeditsremainunstaged;no pushorhistoryrewrite.

## Previous source-verification handoff


## Full-catalog official-source verification completed — 2026-11-22

- Completed topic:fix/full-catalog-source-repair;main after no-ff merge. Registration
  Experiment018committed before implementation/download;inspect git log for commits.
- Read docs/FULL_CATALOG_SOURCE_REPAIR.md first. All1,577original intervals accounted,
  including742pending;788jobs(616funding,151mark,21trade);677HTTP requests plus115
  verified local cache reuses. Replay:788verified checkpoint hits,zero extra requests.
- data/repairs/full_universe/9d8e79788ba25d039b37/containsplan,jobs/rawresponses,
  assessment,verified_case_dispositions,remaining_required_keys,deduplicated observations.
  New23,492marks+1,759funding observations;all122mark intervals' required keys recovered.
- Dispositions:831initialwarmups,9knownpartialeventwarmups,4knownstops,122recovered,
  492funding gap/invalid/stale,101duration-only rule review,4funding interval-unverified,
  11other gaps,2phase terms found(actual completion unverified),1UNFI source conflict.
- Remaining-key CSV has3,868funding feature cutoffs+42flow-hour keys+7close keys.
  These are not missing funding payment counts. No imputation/threshold relaxation.
- Official PUMP/LIT transition CMS bodies saved and verified. UNFI2023-11-30 12:00
  archive totalvolume41538<takerbuy51617.3;REST total122711.7. Quarantined,not replaced.
- All924product-scope rows retained:currentmetadata655COIN,235other nonpremarket
  types,5PREMARKET,29absent. Current labels never justify deleting prior episodes.
  The775provisional figure includes noncrypto/currently reused identifiers;not775coins.
- Newrepair.py,repair_assessment.py,source_evidence.py via onecrypto_factor_researchCLI.
  33active tests+lint pass. No old canonical overwrite,no fit/PnL,no paid data,no push.
- Added observations remain an additive repair artifact;not yet a new integrated
  feature/engine release. Execution_ready=false. Unknown source omissions remain.
- Next:registered duration-definition correction review,dated product/phase scope,
  accepted overlay integration,then all-required-execution-key preflight. Do not run
  another expanded backtest using the unrepaired earlier release or claim full readiness.
- Existing user edits in legacy files remain untouched and unstaged. No deletion
  or broad filesystem restructuring was performed.

## Prior stage handoff (retained for provenance)


## Full-catalog input reconstruction completed — 2026-11-22

- Completed topic: research/full-universe-inputs; current branch main after no-ff
  merge. Registration commit850d68f (Experiment017) predates code/run.
- New src/crypto_factor_research package and config/full_universe_inputs.json;
  no imports of archived Python. One CLI: python -m crypto_factor_research.
- Full924catalog accounted;1,968,120daily /280,896weeklyrows;304Mondays.
  775ever provisional candidates,738outside old37;maximum617simultaneous.
  Zero source-integrity errors. No blanket Size gate/fixed37pool.
- Final dataset:data/features/full_universe/2a39c4222ec6feaa432e;
  manifest sha256:5f0ef4bc76d0915d6cd06e99887524a0d5ff33ca152731b1c18fb06bcd1483c4.
  Classified tables:reports/tables/full_universe_inputs/2a39c4222ec6feaa432e/.
- 1,577raw issue intervals:831normal listing flow warmups,4known stops,
  742remaining review intervals (597funding,122marks,14flow,7close/episode,2phase).
  These are intervals, not asset counts; neither775nor924means executable.
- Local funding series miss2026-06-24 04:00UTC for multiple contracts, explaining
  the June29candidate drop. No value fabricated; check official alternative sources
  next. Existing registration covers local input reconstruction only, no downloads.
- Full build +source/output verified exact cache reuse succeeded;24active tests and
  new package lint pass. Future mutation/gap/episode/funding/corruption tests included.
- Read docs/FULL_UNIVERSE_INPUTS.md and docs/REMEDIATION_PLAN.md. Execution_ready,
  model_fitted,PnL_computed remain false. No new backtest, certified PIT claim or push.
- Old performance applies only to37prototype. All years already inspected remain
  retrospective. User dirty legacy files and untracked tree.json preserved.
- Next segment: targeted official-source repair and complete execution preflight;
  preserve usable dated intervals. Later full-population model/backtest needs its
  own preregistration. Broader legacy architecture migration remains unfinished.

## Previous correction and publication history

The following earlier stage notes are retained for provenance and superseded where
inconsistent with the completed input stage above.


## Full-universe remediation specification and audit -- 2026-11-22

- User resumes work after stopping it and requests complete corrective solutions;
  do not promise perfect/profitable results. No push, deployment or paid data purchase.
- Completed topic research/full-universe-repair-spec:specification plus read-only
  full-catalog audit. Merge this narrow correction/audit into main; the corrected
  dynamic-universe strategy remains unimplemented. Inspect latest merge for commit.
- Read docs/REMEDIATION_PLAN.md first. Covers population,dated eligibility,fees/
  Funding/terminal assumptions,matched momentum/equal-factor/random controls,
  label/holding horizon,migration,naming,cache/run identity and final reporting.
- Existing37pool is a first-prototype subset inherited through2026, not924screened
  down to37. No broad-market or full-project-completion claim is supported by it.
- tools/audit_universe_coverage.py ran on all924daily files:924hashesverified,
  37oldpool,887neverconsidered,787oldcandidateever,750oldcandidatesoutsidepool,
  922withpositivevolume in2021--Oct2026release;GAIB/LENDno positiveactivity there.
- reports/tables/universe_audit/{assets.csv,daily_diagnostic_counts.csv,summary.json}
  are ignored. No data/labels/models/PnL changed, no network calls. New dynamic
  eligibility is explicitly not built or certified by this audit.6focused tests pass;
  READMEpublisher preserves scope corrections and validates them before overwriting.
- All old working edits and untracked tree.json preserved. No full-tree move,
  extra source snapshot or deletion. Previous publication advice is superseded by
  explicit README scope correction. Historical results/contracts remain unchanged.
- Existing historical years may all be used for research; never label seen dates
  as fresh independent OOS. This is not a permission barrier to correcting coverage.
- Next implementation is chronological universe/feature construction plus complete
  repair/assumption queue. Preregister that experiment on main before implementation
  or strategy performance. Do not keep tuning37or claim the larger strategy is done.

## Earlier engineering/publication history

The prior handoff text is retained below for provenance; its readiness statements
are superseded by the scope correction above.


## Local main ready; user will push -- 2026-11-22

- Local main now includes the complete published research tree, badges, new layout
  and explicit full-period/original OOS disclosure. Research merge9a9b4c7; old
  main README is replaced. Completed experiment/publication branches were removed.
- User explicitly chooses to push personally. Assistant must not push or start an
  authentication flow. No remote write performed; origin remains the user's repository.
- Committed candidate code passed356tests+31subtests in isolated snapshot. Subsequent
  changes are documentation only; main code matches tested1e99966 exactly.
- All19original local files restored byte-for-byte; substantive legacy changes remain
  unstaged. Git index is clean. A push sends commits, not those uncommitted changes.
- User command:git push -u origin main (or push main in their authenticated Git client).
  No additional staging or strategy/backtest rerun is required for this publication.


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
