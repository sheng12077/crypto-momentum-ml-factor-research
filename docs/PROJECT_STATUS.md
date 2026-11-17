# Project status

Updated: 2026-11-17.

## Latest result

- Mark recovery protocols: primary `b8991bb`, daily fallback `e1439b8`.
  Completed segment `infra/mark-gap-recovery` targets main via no-ff merge;
  inspect Git for the final merge hash. Report: docs/MARK_GAP_RECOVERY.md.
- Recovered 33,168 of 33,240 exact mark keys, zero source conflicts. All four
  common gaps are covered: 33,096 symbol-hours, zero remaining common-gap keys.
- Full-recovery gate remains FALSE: 72 hours remain (AERGO 11, CTK 11, CVC 9,
  CVX 9, LIT 16, PUMP 7, SLP 9). Official API/daily sources are incomplete there;
  70 hours also lack trade bars. Never interpolate or fill these with zero.
- NEW shared version: data/canonical/binance_um_mark_recovery/v20261117_001_partial/
  contains Parquet, export manifest and quality_mask.json. All rows, exact raw
  prices, timestamps, provenance and recovered/missing target partition verified.
  Existing raw/canonical sources were not overwritten or silently merged.
- Primary API: 1,155 calls, 32,808 rows. Daily fallback: 53 verified ZIPs/checksums,
  40,972 ZIP bytes, 360 additional rows. Cache resume: zero requests and identical
  JSONL digest. All overlay rows remain historical_strategy_eligible=false.
- Context flags: 24 recovered hours after known WAVES closure; 3,192 after the
  last observed positive-volume trade. These are ex-post diagnostics only.
- Evidence under data/interim/usdm_universe: mark_recovery_plan_20261117.json,
  mark_recovery_full_20261117/, mark_recovery_daily_20261117/ (final_validation.json).
- 44 tests, Ruff 0.17.5 and exact-row Parquet validation pass. Primary ran in WSL;
  subsequent WSL launches timed out. Native Python 3.11/PyArrow completed fallback
  and export. No services restarted or system packages changed. Workspace-only
  Ruff lives in ignored data/interim/tooling/ruff_windows. Do not run Windows and
  WSL writers concurrently; their mutex/flock locks are runtime-local.

## Prior evidence and limitations

- Download: 66,893 raw ZIPs, 1,035,606,342 bytes, no errors. Source audit `c31e167`
  verifies all checksums/provenance, exact plan reconciliation, zero corrupt sources.
- Raw superset: 924 identifiers; 655 current-COIN, 239 current-nonCOIN, 30 without
  current metadata. Historical identity is NOT established by this snapshot.
- Trade gaps: 13 files/424 hours remain separate work. Whole funding-month gaps:
  BNT 27, BTCST 1, LIT 5, MDT 15. 54 funding-after-activity identities need review.
- Source reconciliation `589db70`: nine Parquets/183 rows verify; one legacy
  duplicate BTC run lacks Parquet and its original all-runs gate remains failed.
- Original metadata lifecycle gate and exact-12-file pilot also remain failed;
  see docs/historical_universe_feasibility.md and docs/USDM_ACQUISITION.md.
- Strategy direction is a candidate raw/residual momentum comparison. Strategy
  Experiment 001 remains unregistered. No fitting, returns, backtests or orders.

## Next bounded task

Normalize base archives plus this explicit overlay into new versioned research
inputs, preserving the 72-key mask and inactive-data flags. Source lifecycle facts
for the seven remaining-gap identities, funding-month gaps and funding-after-
activity cases before causal eligibility/accounting. Do not revive delisted assets
or use full-history activity endpoints as causal signals.

Reusable tools: scripts/recover_mark_gaps.py, recover_mark_daily.py,
validate_mark_overlay.py; reproducible commands and paths in MARK_GAP_RECOVERY.md.
The WSL wrapper summary now includes primary and daily recovery summaries.
