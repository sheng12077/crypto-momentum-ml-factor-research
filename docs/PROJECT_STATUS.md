# Project status

Updated2026-11-18. Current segment infra/cmc-weekly-coverage, registered on main
at d65d49b; based on ee9f94d. Targets main via no-ff merge; inspect Git for final
merge hash. No push/history rewrite. Scope ends at simulation/OOS; paper/live deferred.

## Current acquisition handoff

- User authorized data preparation; no strategy experiment is registered.
- NEW scripts/collect_cmc_weekly.py; docs/CMC_WEEKLY_COVERAGE.md.
- Frozen official calendar:305 requested dates, all listed;304 Sundays in
  2021-01-01..2026-10-31 plus2020-12-27 carry-in. Plan SHA
  8dd8dd5bde3736138e1efb29ab3915222266cc5d9cd418700ed99cc3d6e6cb46.
- Pilot4 dates/800 rows/387 vendor IDs;2 HTTP requests+2 verified seed reuses.
  Cache resume4 hits/zero HTTP. Raw2,210,747 bytes. No own returns/factors viewed.
- Mapping review924 instruments,259 lexical candidates across FOUR sampled dates;
  ZERO approved histories. BTT and LUNA have multiple vendor-ID candidates. No
  unit conversion, identity joining, eligibility or factor ranking is inferred.
- FULL305-date download NOT RUN. User command in WSL existing environment:
  python scripts/collect_cmc_weekly.py download --max-mib 256
  Then summary --max-mib 256. Root data/interim/cmc_weekly_20261118/;
  log reports/acquisition/cmc_weekly_download_20261118.log. About10min pacing
  plus network/storage; roughly150MiB raw estimate,256MiB hard raw budget.
- Sequential >=2sec requests; bounded retries; stops on access/parse/integrity
  errors. Successful hashes resume. No credentials, subscriptions or purchases.
-71 tests (10 collector) pass; collector Ruff passes. Existing full-tree lint flags
  test_research_data.py import ordering on this native invocation (unchanged).
  Native Python3.11; configured runtime3.13.
  Synthetic one-date full-mode test passes, not evidence real full run completed.

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

1. User completes305-date source download; reconcile final JSON/counts/errors.
2. Review episode-specific vendor IDs and actual missing Size coverage, publication
   lag/revisions; decide whether paid data addresses a measured deficit. Do not
   require every924 ID verified if research universe is declared causally, but do
   not pick a universe by future availability or observed performance.
3. Finish selected lifecycle/specifications/funding/terminal accounting, freeze
   research protocol on main, then implement/validate trading simulation and
   development experiments. OOS disclosed only after final version is frozen.

No factors, training labels, fits, own PnL/backtests or orders computed. Never run
Windows and WSL writers concurrently; local mutex/flock do not coordinate hosts.