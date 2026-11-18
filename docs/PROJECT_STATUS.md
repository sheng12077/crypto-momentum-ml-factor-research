# Project status

Updated 2026-11-18. Current segment: infra/identity-exclusion-decisions, registered
on main at3a68e44; based ond504659. Target main via no-ff merge; inspect Git for
final merge hash. No push/history rewrite. Scope ends at simulation/OOS;
paper/live explicitly deferred until after OOS review.

## Latest completed follow-up

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
- Labels,horizons,holdings,rebalance,buffer,costs,refit and acceptance gates NOT
  frozen;7-day horizon is a candidate,not selected. Nautilus proposed,not installed.
- User reports no2025-26 performance tuning. Draft final OOS2025-01..2026-10 remains
  sealed/unfrozen. Liu/Tsyvinski2021 note docs/literature/liu_tsyvinski_2021.md;
  appendix absent. Conditional means are not executable cross-sectional spreads.

## Next bounded segment

1. Bind reviewed episodes/exclusions into a NEW research-input version; reconcile
   recovered BNX legacy hours there without overwriting existing releases.
2. Measure Size availability in a separately justified historical universe; decide
   missingness treatment or paid data from actual deficits. Do not restart open-
   ended KNC/DYDX searches without specific new evidence or select by future data.
3. Finish lifecycle/specifications/funding/terminal accounting, then freeze the
   strategy/OOS protocol before simulation/development experiments. Final OOS only
   after final version is frozen;paper/live discussion after OOS review.

User need not run commands for this completed follow-up. Never run Windows and
WSL writers concurrently; local locks do not coordinate hosts. No secrets/datasets
committed; reusable tools remain in repo.
