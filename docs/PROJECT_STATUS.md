# Project status

Updated2026-11-18. Current segment docs/unresolved-identity-exclusions, based on
evidence review merge048e962 (protocol ef41192). Documentation-only user decision;
no new experiment or source acquisition. Targets main via no-ff merge; inspect Git for final
merge hash. No push/history rewrite. Scope ends at simulation/OOS; paper/live deferred.

## Current contract identity evidence review

- User allows excluding cases still unverifiable after reasonable official-source
  checks. Prefer affected episodes; if boundaries cannot be established, withhold
  the identifier from automatic joins. Preserve raw data and record reasons,
  intervals, sources, decision time and historical availability basis.
  Missing Size alone is a separate data gate, not proof an asset is untradable.
  No new named exclusions or final universe applied in this docs-only update.
  Ex-post subset selection must be disclosed; pre-OOS freezing alone does not
  eliminate selection bias. Details in CONTRACT_IDENTITY_EVIDENCE.md.

- User authorized evidence review, not a strategy experiment. All27 priority IDs
  reviewed against39 captured official Binance notices (30 new requests,9 seed
  reuses;2,365,948 raw bytes). No payment, keys or OOS performance inspection.
- NEW config/contract_identity_evidence_20261118.json and reusable
  scripts/review_contract_identity.py; findings docs/CONTRACT_IDENTITY_EVIDENCE.md.
  41 source-term assertions,35 proposed episodes,25 with proposed vendor IDs.
  No historical joins approved; partial evidence does not certify vendor-chain
  identity, complete lifecycle, units or original publication/content vintage.
- Ignored evidence data/interim/contract_identity_review_20261118/;
  final review_002/ contains mapping proposals, source manifests,506-ID triage
  and summary. Initial review/ retained before strengthened validation/CMS fields.
- BNX old/new split:2023-02-11 04UTC settlement;2023-02-22 14:45UTC relaunch;
  old route BNXUSDTSETTLED. New episode closes2025-03-17 09UTC; archive span
  extends beyond closure and remains unreconciled. No new legacy download yet.
- Reject Strike8911 for Starknet STRKUSDT, and newTerra20314 as continuation of
  old LUNAUSDT. LIT/PUMP pre-market modes explicitly retained; no switch to
  regular assumed. Later MDT is Medtronic equity, not the earlier crypto token.
- SHIB launch explicitly defines1000 underlying tokens per price unit. SATS spot
  bundle corroborates1000 units but CMC28194/28683 identity/denomination unresolved.
  Other label-derived scales remain unverified specs; no USD cap multiplication.
- 506 absent-candidate IDs:251 have some triage lead,255 none; all absence reasons
  unresolved.236 current noncoin annotations and15 scaled flags overlap priority
  leads; none is a causal exclusion rule or proof of a below-top-200 absence.
- 84 tests pass (7 new); new script/tests Ruff pass. Native Python3.11; configured
  runtime3.13. Unchanged full-tree native import-order lint remains below.

## Completed identity/coverage audit

- User authorized data preparation; no strategy experiment is registered.
- scripts/collect_cmc_weekly.py; docs/CMC_WEEKLY_COVERAGE.md.
- Frozen official calendar:305 requested dates, all listed;304 Sundays in
  2021-01-01..2026-10-31 plus2020-12-27 carry-in. Plan SHA
  8dd8dd5bde3736138e1efb29ab3915222266cc5d9cd418700ed99cc3d6e6cb46.
- User completed FULL305-date acquisition:61,000 rows/662 vendor IDs,301 HTTP,
  4 cache hits,151,839,940 raw bytes,zero errors;all dates200 rows.
- Mapping review924 instruments,418 lexical candidates across full calendar;
  ZERO approved histories. Nine IDs have multiple vendor-ID candidates. No
  unit conversion, identity joining, eligibility or factor ranking is inferred.
- Source root data/interim/cmc_weekly_20261118/; original acquisition unchanged.
  No repeat download needed. Pilot cache resume previously4 hits/zero HTTP.
- Sequential >=2sec requests; bounded retries; stops on access/parse/integrity
  errors. Successful hashes resume. No credentials, subscriptions or purchases.
- NEW offline scripts/audit_cmc_identity.py and docs/CMC_IDENTITY_AUDIT.md.
  Derived version data/interim/cmc_identity_audit_002_20261118/; no HTTP.
  Initial attempt verified all source/parsed inputs, then failed on null trade
  archive month bounds in aggregation. Preserved initial output/config; fixed
  unknown-bound handling and added regression coverage before version002.
- Version002 SUCCESS:305 source/raw/parsed dates,61,000 rows/662 vendor IDs,
  zero errors. Queue:506 without literal candidates,9 multi-ID histories,
  3 known reuse,16 possible scaled,23 vendor IDs with raw symbol variants;
  flags overlap. GAIBUSDT/LENDUSDT missing trade bounds explicitly retained.
  All61,000 row availability/vintage unproven;zero mappings approved.
  Annual archive-month-span lexical proxy80.1% in2021,48.6% in2024,20.7%
  in2026 Jan-Oct; includes noncrypto/scaling/label issues, NOT approved coverage
  or a paid-data requirement. Full counts/limitations in CMC_IDENTITY_AUDIT.md.
- 77 tests pass; six new audit tests include offline resume, corruption, independent raw reparsing,
  same-date-only lexical counts, null archive bounds and no mapping approval.
  New code Ruff passes. Existing full-tree lint flags
  test_research_data.py import ordering on this native invocation (unchanged).
  Native Python3.11; configured runtime3.13.
  Native validation details/results in CMC_IDENTITY_AUDIT.md.

## Existing data and readiness

- Original normalized release shared canonical/binance_um_research/v20261117_001/:
  full66893 partitions; trade16217181, mark16418784, funding2811083; total35447048.
  Overlay33168 integrated. Build succeeded in user's WSL funding-strategy Conda.
  Original input/embedded lifecycle hashes unchanged. Engineering merge6730302,
  full-result docs d771ea2. Old embedded lifecycle is still21 sources/47 events.
- NEW supplemental lifecycle_review_20261118/ and config/lifecycle_facts_20261118.json:
  52 official sources/91 events/64 IDs;61/61 priority IDs have partial evidence,
  ZERO full lifecycles. Ex-post facts only; causal_available_at=null.
- Known PUMP legacy settlement2025-06-13 09UTC -> PUMPBTCUSDT10UTC; July PUMP is
  Pump.fun. LIT=legacy Litentry/later Lighter; MDT=legacy/later Medtronic equity.
  OMG postponements resolved to2025-01-31 09UTC. DOTECO is an index, not a token.
  Supplement is not silently attached to old release; bind reviewed metadata later.
- Readiness protocol b863dc2 / merge ee9f94d. docs/RESEARCH_INPUT_READINESS.md.
  CMC2-date pilot400 rows; Coin Metrics32/32 BTC/ETH observations and135 vendor
  IDs. Coin Metrics current-issued-supply cap differs from CMC circulating cap.
  Full Size history, episode-ID mapping, original vintage/availability UNRESOLVED.
- Funding11 partitions/969 rows hash/count verify;12 BTC/ETH API2021 rows exactly
  match archived times/rates, but associated markPrice empty. Max timing offset
  20ms preserved.106 after-captured-closure rows are EX-POST flags, not cashflows.
  Actual settlement notional/prices, event ordering, source availability and
  terminal accounting remain unverified. Do not infer exact price from hourly OHLC.

## Research discussion: not a frozen experiment

- Four candidates: momentum20/60/120, Size, funding, taker trade imbalance.
  User accepts rank buffer and requires SHAP. Equal composite baseline/LightGBM
  challenger discussed. News/NLP deferred. NautilusTrader proposed for formal
  simulation; no dependency/engine integration implemented yet.
- Labels/horizons, holdings, rebalance, buffer cutoffs, costs, refit and gates NOT
  frozen.7-day horizon is literature-supported candidate, not optimal/selected.
- User reports no strategy-performance tuning using2025-26. Proposed final OOS
  2025-01..2026-10 remains a DRAFT; no own strategy OOS performance inspected.
- Liu/Tsyvinski2021 main article reviewed, merge fbf5781; note
  docs/literature/liu_tsyvinski_2021.md. Appendix missing. Aggregate weekly
  conditional means are not executable cross-sectional spreads. Section4.2
  three-week sign/one-week holding needs appendix calendar/weight/cost details.

## Preserved limitations and prior failed gates

- Raw66893 ZIPs/1,035,606,342 bytes checksum/provenance verified (c31e167).
  924 IDs !=924 crypto assets; current655COIN/239nonCOIN/30absent is an annotation,
  not historical membership. No eligible universe is certified.
- Mark recovery cd9f09d (protocols b8991bb/e1439b8):33168/33240 keys, zero conflicts;
  four common gaps33096 hours covered;72 unresolved across seven IDs,70 also trade.
  Shared canonical/binance_um_mark_recovery/v20261117_001_partial/ unchanged.
- Trade424 interior hours/13 files;1913 constant zero-volume files. Funding month
  gaps BNT27/BTCST1/LIT5/MDT15. CVX/SLP/LIT archive/current-announcement launch
  timing conflicts unresolved. No gaps waived or zero-filled.
- Old exact12 pilot actually11, original lifecycle gate, legacy duplicate BTC
  missing Parquet remain FAILED. Reconciliation589db70 verified nine other
  Parquets/183 rows. No old gate silently upgraded.

## Next bounded work

1. Acquisition completed; derived audit/queue in CMC_IDENTITY_AUDIT.md.
2. First27-ID evidence review completed (CONTRACT_IDENTITY_EVIDENCE.md). Next
   resolve vendor chain/contract/denomination, BNX legacy routing, futures KNC/SUN/
   DYDX transitions, pre-market modes and unexplained post-closure observations.
   Then measure usable Size coverage and publication/vintage deficits; decide
   whether paid data addresses a measured deficit. Do not
   require every924 ID verified if research universe is declared causally, but do
   not pick a universe by future availability or observed performance.
3. Finish selected lifecycle/specifications/funding/terminal accounting, freeze
   research protocol on main, then implement/validate trading simulation and
   development experiments. OOS disclosed only after final version is frozen.

No factors, training labels, fits, own PnL/backtests or orders computed. Never run
Windows and WSL writers concurrently; local mutex/flock do not coordinate hosts.
