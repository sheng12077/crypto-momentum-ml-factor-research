# Project status

Updated 2026-11-18. Current segment: infra/history-extension-inventory, registered
on main atfc0238c. Inspect Git for final no-ff merge hash.
Weekly contract registered on main atee792fa. Inspect Git for final merge hash.
Daily implementation registered on main at93cf6e1. Target main via no-ff merge; inspect Git for
final merge hash. No push/history rewrite. Scope ends at simulation/OOS;
paper/live explicitly deferred until after OOS review.

## Early-history/funding extension before portfolio experiments

- User authorized backfill toward2019 and associated funding inputs;hold portfolio
  specification while data work proceeds. docs/HISTORY_EXTENSION.md has findings
  and tested WSL command. Existing release/calendar/training/OOS unchanged.
- Tool extend_usdm_history.py verifies924 identifiers/2772 cached listing jobs,
  full pagination/URL/hash integrity;97.688s,zero metadata HTTP. Reparsed old
  66893-file/1035606342-byte totals match frozen census. No old tools modified.
- Frozen archive evidence has no2019 monthly files;2020 extension1526 files/
  24153565 bytes/81 IDs:trade509,mark510,funding507;zero checksum gaps.
  Monthly three-series file presence11 Jan/30 Jun/80 Dec,not eligible counts.
- BTC/ETH January2020 six-file pilot124307 bytes passes;resume6 hits/0 downloads.
  Full extension NOT downloaded. WSL:python scripts/extend_usdm_history.py
  download --max-gib 0.03 --workers 2;then summary. Raw readiness only.
- probe_2019_history.py made3 bounded BTC2019-09-14 API requests,allHTTP200:
  trade1bar,mark0,funding2events with missing markPrice. Sample availability only;
  full2019 coverage unproven. Cached evidence retained,no retries/alternatehosts.
- Funding archive/bar mismatches queue163 identifiers over2019--2026-10;not
  proven missing settlements. Need interval/time/unit/sign/event-price/terminal
  reconciliation;hourly mark cannot silently substitute for exact event mark.
- 134 tests pass (13 new),new files Ruff lint/format pass. No model/returns/PnL/
  OOS performance. Next raw backfill,normalization,funding/early Size/identity
  checks;training extension needs protocol amendment,not silently edited dates.

## Completed full weekly coverage

- User WSL full scan succeeds7.979s,924 IDs/209 dates/errors[];local count artifacts
  checked. Assumed-Size candidates0/102/142 min/median/max;192/209 weeks>=20.
- All17 below20 are2021-01-04..2021-04-26 with zero price/funding candidates,
  consistent with120-day warm-up. First passing2021-05-03:68 assumed-Size.
  2023 min99/median120/max131;2024 min112/median133/max142.
- 2022-08-01 is the only post-warm-up week below50:29 assumed-Size,44 price/
  funding;cause unresolved. Do not infer liquidity or Size-only explanation.
- No returns/labels/fits/PnL/OOS performance inspected;strict eligibility false.
  Next specify holdings/exposures,features/model/refit,cost/funding/terminal gates.

## Latest weekly baseline stage 0 and coverage handoff

- Registered experiments/001_weekly_baseline_stage0.md + machine-readable
  config/weekly_baseline_v1.json before implementation. Tools weekly_contract.py
  and check_weekly_baseline.py;docs/WEEKLY_BASELINE_STAGE0.md has full command.
- Research assumptions:Monday00UTC cutoff,01decision,01--02hour VWAP entry/
  next-week exit,exit-end+1h assumed label availability. Label later is simple
  seven-day proxy return before costs/funding. No values computed. These are
  not verified exchange publication latency or actual fills.
- 209 development dates;round1 train103/validation51 time-only usable,round2
  train155/validation52;one boundary purge per period. No2025+ projected rows,
  no prices/returns/PnL/modelfit;strict Size/readiness remainfalse.
- BTC/BNX/SUN pilot passes15.422s,resume13.125s/3hits;assumed-Size counts
  min0,median1,max2 in this subset only. Full924 scan subsequently completed
  by user;results above. No rerun required for this result review.
- 121 tests pass (10 new);changed-file Ruff lint/format pass. Native3.11/Arrow11.
  Holdings/models/refit/costs/funding/terminal and performance gates pending.

## Approved weekly research sequence

- User approved docs/WEEKLY_RESEARCH_SEQUENCE.md:one-week prediction/weekly
  portfolio baseline,independent rank-buffer experiment,then position adjustment.
  Stage0 fixes target/clock assumptions;20/60/120 sizing remains a candidate.
- Isolate buffer on the same schedule;daily monitoring is a separate frequency
  comparison. Separate resizing turnover from membership changes. Later sizing
  needs comparable exposure/risk;do not credit lower exposure as signal quality.
- Literature anchors recorded with version limits. No performance/fit/OOS run.
  This direction record is not the complete preregistration;fees,universe,
  holdings,models,refit and numerical acceptance thresholds remain to resolve.

## Approved split and user-reported full build

- User approved docs/RESEARCH_SPLIT.md:train2021-22/validate2023;
  train2021-23/validate2024;sealed final OOS2025-01 through2026-10,all UTC.
  Trailing pre-boundary history allowed;overlapping training labels excluded.
  Exact sample endpoints await target/execution timing;no random row split.
- Full WSL build reported successful:223.383s,errors[],924 IDs/1968120 rows/
  66893 source partitions/244 legacy BNX hours. Ever-passing diagnostics787
  price/funding,338 assumed-Size four-factor,338 class-review-clear,0 strict.
  Not simultaneous tradable counts;readiness/strict Size vintage remainfalse.
- No strategy performance/OOS inspection. Weekly target/clock fixed for stage0;
  refit and complete trading protocol remain pending.

## Latest daily-input implementation and handoff

- docs/DAILY_RESEARCH_INPUTS.md has the full WSL command and expected manifest;
  scripts/build_daily_inputs.py + daily_input_rules.py build new immutable daily
  sidecars. No factor returns/labels/fit/PnL, downloads or OOS performance viewed.
- Fixed five-identifier pilot passed:759 daily rows,102 source partitions verified,
  244 legacy BNX hours consumed;267 post-close archive hours excluded. Initial
  17.328s;verified resume11.031s/five hits. Source releases remain unchanged.
- Per-row episode resets,24-hour completeness,121-close history vs20/60/120
  endpoints,strictly earlier same-episode funding and scoped policy enforced.
  Unknown lifecycle/settlement accounting remain unresolved;no final universe.
- Size uses separately labelled diagnostic snapshot-end+7d availability/7d expiry.
  Publication/revision vintage is unproven;strict eligibility/readiness stayfalse.
  Pilot distinct candidates:price/funding3,assumed-Size four-factor2,strict0.
  Current classifications are ex-post annotations,not a causal universe.
- 111 tests pass;new builder/rules/tests Ruff lint/format pass. Native3.11/Arrow11;
  configured project3.13. Full daily build subsequently run by user in WSL Conda.
  Expected924 IDs/1968120 rows/66893 source partitions,not924 tradable assets.
- User supplied full manifest;calendar splits now approved above. Label overlap
  details and the remaining strategy protocol still precede experiments.

## Latest completed full-universe retention screen

- User clarified: retain as many usable assets as possible, not maximize exclusions.
  All924 IDs screened;923 have some files,922 positive-volume trade observations.
  GAIB has mark/funding but no trade;LEND has no files. No whole-history deletion
  for a local gap/stub/current classification;all raw/research releases unchanged.
- docs/FULL_UNIVERSE_RETENTION_SCREEN.md; tools scripts/screen_full_universe.py
  and scripts/export_screen_candidates.py. Full22635 trade acquisition reports
  validated in91.391s;zero errors. Trusts prior raw checksum audit,not fresh ZIP
  or every-Parquet/hourly-close verification. No downloads/OOS performance viewed.
- 426 Size-history ID leads after component blocks;405 have potential overlap
  with an active month. These are contract identifiers,not necessarily distinct
  crypto coins,simultaneous holdings,valid daily joins or a final universe.
  789 have possible120-day elapsed span only;episode resets/gap-free closes not
  validated. None of these cohorts necessarily has the same membership.
- 149 identifiers with stub months retained in other months. KNC/DYDX/MDT still
  Size-blocked,8 scoped restrictions attached for later row-level application.
  Current239noncoin/30missing metadata not automatic historical exclusions.
  405 Size-month leads include22 missing-current-metadata names;NUUSDT is the one
  current-noncoin annotation requiring identity/episode review within this cohort.
- Ignored data/interim/full_universe_screen_20261118/: quick/review_queue.json;
  full/checkpoints,indexes,yearly_instrument_month_counts,summary;exports/ named
  candidate_lists.json and enriched review_queue.json. All924 checkpoint hashes
  and cohort/report counts reconciled by exporter. No user command needed.
- Five-asset pilot248 reports1.016s;resume5 checkpoint hits0.421s. Full run executed
  because pilot was fast;no remaining full metadata scan handoff. Initial loader
  ledger/file-population assumptions fixed;failed logs preserved,final full passes.
- 99 tests pass (6 new);new scanner/exporter/tests Ruff lint/format pass. Native
  Python3.11;configured runtime3.13. Existing unrelated native import-order lint
  unchanged. Formal eligibility/automatic joins remain false;no factors or PnL.

## Previous completed identity follow-up

- User authorized checking and conservative exclusions where identity/specification
  evidence cannot be established. Exclusions are ex-post data-join restrictions,
  not a certified causal universe. Preserve raw data and reasons; missing Size
  alone does not prove nontradability. No strategy performance/OOS inspection.
- Findings: docs/IDENTITY_FOLLOWUP_DECISIONS.md. Sources/query log:
  config/identity_followup_sources_20261118.json; policy:
  config/identity_decisions_20261118.json. Tools: scripts/check_identity_followup.py
  and scripts/build_identity_decisions.py. Ignore generated data artifacts.
- All27 priority cases decided:24 retained identity candidates,3 temporary whole
  Size-join exclusions (KNCUSDT,DYDXUSDT,MDTUSDT),8 interval/scope restrictions.
  Retention is NOT join/trading approval. KNC/DYDX futures switch evidence remains
  unestablished; MDT legacy mapping unresolved and later episode is equity.
- SUN launch verified2024-08-22 13:05UTC, after2021 spot migration. CMC10529 full
  Tron address matches official migration source; discard old6990 association for
  this contract. Prior futures-migration concern corrected, old report preserved.
- SATS/1000SATS same-asset denomination supported by cached official rendering;
  direct bundle page now404. Preserve excerpt/provider limits. Primary historical
  candidate28683; alternate28194 NOT automatically spliced; no USD cap scaling.
- Baby Doge case-sensitive lookup corrected:CMC10407 has61 captured snapshot
  dates (not61 tradable observations). BOB34422,CAT32724,rats28452,WHY30867,
  X33108 current IDs identified but have ZERO dates in captured first-page history.
  Missing Size treatment/data requirement remains; no automatic whole-asset drop.
- BNX7 existing raw/normalized partitions verified by checksum/hashes/times/counts.
  Late2025-04/2026-10 trade is fixed-price/zero-volume; sampled mark is also fixed.
  March2025 settlement-hour positive bar is NOT proven executable after closure.
- BNXUSDTSETTLED official listing and February2023 ZIP/checksum verified:
  511 rows,244 positive-volume legacy hours,267 post-close zero-volume rows.
  Current BNXUSDT February starts at new relaunch; legacy hours NOT integrated.
  Relaunch-hour bucket14:00 does not prove trading before14:45 launch.
- Ignored root data/interim/identity_followup_20261118/: final audit_003/ and
  decisions/. Earlier audit versions retained.17 source URLs:15 success,one404,
  one REST probe exhausted3 failures; raw7,336,544 bytes. Capture success=false
  is preserved; bounded audit and decisions succeeded. Do NOT retry REST/downloads
  merely to turn this flag green. No access denial bypass, keys or purchase.
- 93 tests pass (9 new); new scripts/tests Ruff lint and format pass. Native
  Python3.11/Arrow11; configured runtime3.13. Existing unrelated native full-tree
  import-order lint in tests/test_research_data.py unchanged. No final universe,
  automatic historical joins, factor/label/fit/PnL or orders; readiness stays false.

## Existing releases and evidence

- Shared canonical/binance_um_research/v20261117_001/:66893 partitions;
  trade16217181,mark16418784,funding2811083 (total35447048); overlay33168.
  User built successfully in WSL funding-strategy Conda. Original source/lifecycle
  hashes unchanged; embedded lifecycle remains21 sources/47 events.
- Supplemental lifecycle_review_20261118/ + config/lifecycle_facts_20261118.json:
  52 sources,91 events,64 IDs;61/61 priority IDs have partial evidence,zero full
  lifecycles. Ex-post only,causal_available_at=null. Never silently attach to old
  release. Known LIT/PUMP/MDT reuse; PumpBTC settles2025-06-13 09UTC, relists as
  PUMPBTCUSDT10UTC; laterPUMP is Pump.fun. OMG final close2025-01-31 09UTC;
  DOTECO is index. Details in LIFECYCLE_REVIEW.md and evidence configs.
- Full CMC acquisition305 dates/61000 rows/662 IDs,zero errors,151839940 raw bytes;
  four-date resume zeroHTTP. Root cmc_weekly_20261118/. No repeat download.
  PlanSHA8dd8dd5bde3736138e1efb29ab3915222266cc5d9cd418700ed99cc3d6e6cb46.
- Audit merge70e06ef: cmc_identity_audit_002_20261118/ verified all raw/parsed;
  924 identifiers,418 literal candidates,506 absent,9 multi-ID histories,16 scaled
  flags,23 raw-symbol variants. GAIB/LEND missing trade bounds retained. All61000
  cap rows have unproven availability/vintage. Annual archive-month lexical proxy
  includes noncrypto/scaling and is NOT usable Size coverage or a buy-data metric.
- Evidence merge048e962:39 official captures,41 assertions,35 proposed episodes;
  25 vendor-ID proposals. config/contract_identity_evidence_20261118.json;
  contract_identity_review_20261118/review_002/. Source bytes preserved; follow-up
  decisions supersede listed unresolved SUN/Baby/SATS proposals only as documented.
- Readiness mergeee9f94d: Coin Metrics32 BTC/ETH observations/135 IDs; current
  issued-supply cap differs from CMC circulating cap. Funding11 partitions/969 rows;
  12 API events match rate/time but markPrice empty,max boundary offset20ms.
  106 post-captured-close flags are ex-post,not proven cashflows. Actual settlement
  notional/prices,ordering,terminal accounting and source availability unresolved.

## Preserved limitations

- Raw66893 ZIPs/1035606342 bytes provenance/checksum verified.924 identifiers are
  not924 crypto assets; current655COIN/239nonCOIN/30absent are annotations only.
- Mark recovery33168/33240 keys;four common gaps33096 hours covered;72 unresolved
  over7 IDs,70 also trade. Partial canonical mark release unchanged. Trade424
  interior hours/13 files,1913 constant zero-volume files. Funding month gaps
  BNT27/BTCST1/LIT5/MDT15;CVX/SLP/LIT archive/announcement timing conflicts remain.
- Old exact12 pilot actually11, original lifecycle gate and legacy duplicate BTC
  missing Parquet remain FAILED. Reconciliation589db70 verified9 other Parquets/
  183 rows;no waived gaps,zero filling or silent gate upgrades.

## Research decisions still deferred

- Candidates:momentum20/60/120,Size,funding,taker imbalance. Rank buffer accepted;
  SHAP required. Equal composite baseline/LightGBM challenger discussed; NLP later.
- Weekly baseline target/clock assumptions registered;holdings,buffer,
  costs,refit and acceptance gates NOT frozen. Nautilus proposed,not installed.
- User reports no2025-26 performance tuning. Final OOS2025-01..2026-10 calendar
  approved and sealed;full protocol not frozen. Liu/Tsyvinski2021 note docs/literature/liu_tsyvinski_2021.md;
  appendix absent. Conditional means are not executable cross-sectional spreads.

## Next bounded segment

1. Complete the separate early RAW extension from HISTORY_EXTENSION.md,then
   normalize/reconcile funding and earlier Size/identity. Portfolio work held.
2. Measure Size availability in a separately justified historical universe; decide
   missingness treatment or paid data from actual deficits. Do not restart open-
   ended KNC/DYDX searches without specific new evidence or select by future data.
3. Finish lifecycle/specifications/funding/terminal accounting, then freeze the
   strategy/OOS protocol before simulation/development experiments. Final OOS only
   after final version is frozen;paper/live discussion after OOS review.

Original daily build/weekly coverage complete;early RAW download handed off. Never run Windows and
WSL writers concurrently; local locks do not coordinate hosts. No secrets/datasets
committed; reusable tools remain in repo.
