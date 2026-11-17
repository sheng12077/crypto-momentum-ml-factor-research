# Project status

Updated: 2026-11-17. Current segment: infra/research-data-layer, registered on main
at f622b1b. Engineering work targets main via no-ff merge; inspect Git for the
final segment/merge hash. No remote push or history rewrite.

## Latest bounded result

- User authorized stages 1 (research data layer) and 2 (lifecycle review).
  Stage 3 strategy, exact OOS splits, fit, costs and selection rules are DEFERRED.
- Implemented scripts/build_research_data.py, review_usdm_lifecycle.py,
  run_research_data.py, src/momentum_data reader and curated official facts.
- FINAL pilot normalization_pilot_004_20261117: 34/34 partitions; 8767 trade,
  8768 mark, 960 funding, 72 overlay rows. Fresh build and 34-hit cache resume pass.
  Raw hashes/counts, exact decimal strings, UTC semantics, unique keys and Parquet
  roundtrip verified. Pilot 001 failed a Windows handle/rename; 002 passed after
  handle closure; 003/004 also bind lifecycle evidence. Failed artifacts retained.
- FULL 66,893-partition normalization NOT RUN; prepared/tested cross-platform
  entry point. User execution: python3 scripts/run_research_data.py build
  (WSL Python with Arrow), then summary. Windows alternative: py -3.11.
  Instructions, output/log paths and exact success criteria: RESEARCH_DATA_LAYER.md.
- Lifecycle ledger covers all 924 identifiers, with 21 captured official CMS
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
  prevented native-WSL execution; configured project runtime remains Python 3.13.
  Mypy unavailable/not run. No service restart or system environment change.

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

1. User executes full conversion and returns final machine summary; reconcile
   exact counts before calling the full release ready. Expected release shared
   canonical/binance_um_research/v20261117_001/; old sources remain untouched.
2. Continue lifecycle evidence for the 38 unsourced priority IDs and timing
   conflicts; terminal prices/cashflows and historical content availability remain
   unresolved even for sourced IDs. See LIFECYCLE_REVIEW.md.
3. Discuss and preregister the concrete strategy and precise chronological OOS/fit
   protocol BEFORE implementing factors, performance analysis or fitting.

No returns, rankings, fit, backtest, strategy thresholds, orders or OOS boundaries
were computed/chosen. Do not run Windows and WSL writers concurrently (local locks).