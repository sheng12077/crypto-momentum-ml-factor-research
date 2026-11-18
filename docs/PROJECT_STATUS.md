# Project status

Updated: 2026-11-18. Engineering merged at 6730302; protocol f622b1b.
Current segment: infra/research-input-readiness, protocol b863dc2 on main;
targets main via no-ff merge. No remote push or history rewrite.

## Latest bounded result

- User authorizes research-input readiness work (step1), plus design discussion.
  Scope ends at historical simulation and OOS review; paper/live deferred.
  Exact OOS dates, labels, costs and selection rules are NOT frozen.
- Implemented scripts/build_research_data.py, review_usdm_lifecycle.py,
  run_research_data.py, src/momentum_data reader and curated official facts.
- FINAL pilot normalization_pilot_004_20261117: 34/34 partitions; 8767 trade,
  8768 mark, 960 funding, 72 overlay rows. Fresh build and 34-hit cache resume pass.
  Raw hashes/counts, exact decimal strings, UTC semantics, unique keys and Parquet
  roundtrip verified. Pilot 001 failed a Windows handle/rename; 002 passed after
  handle closure; 003/004 also bind lifecycle evidence. Failed artifacts retained.
- FULL normalization completed by user in WSL using funding-strategy Conda env.
  Local release manifest reconciles: success/full_scope=true, errors=[], 66893/66893
  partitions; trade 16217181, mark 16418784, funding 2811083; total 35447048 rows.
  Overlay expected/integrated 33168, cache_hits=0. Builder SHA and copied lifecycle
  event/ledger hashes independently match manifest. This follow-up checked metadata
  and input hashes; it did not reread every partition or rerun the conversion.
  Full-cache resume has not been run. Release normalization gate passes; historical
  eligible-universe gate remains FALSE. See RESEARCH_DATA_LAYER.md.
- The FROZEN release embeds the earlier ledger for924 IDs, with21 official CMS
  sources and 47 curated events for 25 identifiers. Priority union 61; 23 have
  partial event evidence, 38 have none yet. ZERO complete lifecycles verified.
  Outputs: data/interim/usdm_universe/lifecycle_review_20261117/.
- LIT (Litentry/Lighter), PUMP (PumpBTC/Pump.fun), MDT (legacy/Medtronic equity)
  reuse tickers. Reader rejects known reuse/settlement crossings, never fills gaps.
- All 72 unresolved mark keys are before/in current-announcement launch hours;
  archive observations for CVX/SLP/LIT also precede those announcement times.
  Historical versions/trading semantics remain unresolved; masks NOT waived.
- Events are ex-post only, causal_available_at=null. Funding observations do not
  establish payable cashflows. All historical eligibility remains FALSE.
- 51 tests and Ruff pass on native Python 3.11.5/Arrow 11.0.0. WSL launch timeouts
  prevented agent-run WSL tests at implementation time; user subsequently completed
  full WSL conversion. Configured project runtime remains Python 3.13.
  Mypy unavailable/not run. No service restart or system environment change.

## Current research discussion (2026-11-18)

- Four candidate components: momentum 20/60/120, Size, funding, taker trade
  imbalance. Size data still need historical point-in-time coverage/identity.
  News/NLP is deferred to a later project. No factor is presumed profitable.
- User accepts rank-buffer concept and makes SHAP mandatory. Equal-score
  baseline plus LightGBM challenger discussed; no target label/task is selected.
  Capacity, buffer cutoffs, retraining and trading schedule remain undecided.
- User reports no strategy/factor-performance-driven tuning on 2025-2026.
  2025-01..2026-10 is only a proposed sealed final OOS; dates not preregistered.
  No own strategy/factor returns, fits or OOS results have been computed/viewed.
- Reviewed supplied FINAL Liu/Tsyvinski 2021 main article (39 journal pages).
  Note: docs/literature/liu_tsyvinski_2021.md. Internet Appendix not supplied.
  Weekly aggregate forecast tests differ from cross-sectional long/short.
  Table 6's OOS uses first-two-year tercile cutoffs; high-low conditional means
  are not simultaneous tradable spreads. Section 4.2 uses 3-week return sign,
  1-week holding; calendar/weights/selection/cost details need its appendix.
  Seven-day forecast/holding is a justified candidate, not an optimal/frozen rule.

## Research-input readiness audit (2026-11-18)

- Protocol b863dc2. Report docs/RESEARCH_INPUT_READINESS.md. Diagnostic checks
  pass; complete research inputs and historical eligible universe remain NOT READY.
- CMC public snapshot pilot20210103/20240107:200 each/400 rows, no login/key.
  Coin Metrics Community:135 daily-cap vendor IDs;32/32 BTC/ETH pilot rows.
  Current-issued-supply cap differs from circulating/free-float cap. Historical
  publication versions/latency unknown. Do NOT splice definitions or buy data yet.
- All924 have mapping review entries. Lexical leads only: CMC187 across TWO dates,
  Coin Metrics63; ZERO approved historical mappings. Not full-history coverage.
- NEW config/lifecycle_facts_20261118.json; NEW lifecycle_review_20261118 audit:
  52 sources,91 events,64 identifiers with events;61/61 priority IDs now have
  partial evidence (previously23/61). ZERO full lifecycles; ex-post only.
- PUMP legacy closed2025-06-13 09UTC, relisted PUMPBTCUSDT10UTC; July PUMP is
  Pump.fun. OMG final postponed close2025-01-31 09UTC. DOTECO is a composite
  index, not a separate token; official launch/close sourced. No free rolls.
- Funding11 partitions/969 rows hash/count verify. Twelve BTC/ETH API2021 events
  exactly match archive times/rates; associated markPrice empty. Max interval-
  boundary offset20ms preserved.106 rows after captured closure are ex-post
  flags only, not proven invalid/paid. Cashflow/settlement-price gates remain false.
- scripts/check_research_inputs.py produces readiness/coverage/provenance and
  compact summary under data/interim/research_input_readiness/20261118/.
  Final resume9 HTTP cache hits/zero fetches.61 tests (10 new), Ruff pass.
- Original full observation release and embedded OLD lifecycle snapshot unchanged.
  New supplement is not silently used by ResearchData; future engine inputs must
  explicitly bind reviewed metadata. No factors/labels/PnL/OOS performance computed.
- User has CG/CMC accounts but uncertain about paid plans; no credentials/purchases.
  Next: full-calendar CMC weekly coverage plan and episode-ID review, then assess
  remaining daily history needs. Register settlement-price approximations, if any,
  separately from factual data validation. No full cap history acquired this turn.

## Preserved prior evidence

- Prior main merge cd9f09d: mark recovery. Protocols b8991bb / e1439b8.
- Raw acquisition: 66,893 ZIPs / 1,035,606,342 bytes, all verified (audit c31e167).
  924 identifiers != 924 crypto assets: current snapshot 655 COIN, 239 nonCOIN,
  30 absent. Snapshot annotations are not historical identity/membership.
- Mark overlay: 33,168/33,240 recovered, zero conflicts. All four common gaps
  (33,096 symbol-hours) covered; 72 missing across seven IDs remain (70 also trade).
  Shared canonical/binance_um_mark_recovery/v20261117_001_partial/.
  Overlay SHA256: 01c261dbcb8adf7e1b1123983132ee8c166c81082aedc654315054538ac93926.
  24 overlay hours after WAVES closure and 3192 after last observed trade activity
  are ex-post audit flags only. MARK_GAP_RECOVERY.md retains detailed evidence.
- Trade gaps 424 hours/13 files; 1913 constant zero-volume trade files.
  Funding whole-month gaps BNT27/BTCST1/LIT5/MDT15; 54 funding-after-activity IDs.
- Old exact-12 pilot actually11, original metadata lifecycle gate, and legacy
  duplicate BTC run missing Parquet remain FAILED. Source reconciliation 589db70
  verified nine other Parquets/183 rows. No historical gate silently upgraded.

## Next bounded tasks

1. Full conversion gate passed. Shared observation release exists at
   canonical/binance_um_research/v20261117_001/. No further full conversion
   is required for this stage; strategy eligibility is still unverified.
2. First-step audit completed to bounded pilot scope. Expand cap calendar/ID
   coverage, resolve selected contract episodes/specifications and terminal prices.
   All61 priority IDs have partial sources; actual causal/cashflow readiness is
   unresolved. See RESEARCH_INPUT_READINESS.md.
3. Discuss and preregister the concrete strategy and precise chronological OOS/fit
   protocol BEFORE implementing factors, performance analysis or fitting.

No returns, rankings, fit, backtest, strategy thresholds, orders or OOS boundaries
were computed/chosen. Do not run Windows and WSL writers concurrently (local locks).