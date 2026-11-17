# Project status

Updated: 2026-11-17.

## Current conclusion

- Latest segment: bounded mark-gap reconciliation, preregistered `7d4f078`,
  topic `infra/mark-gap-reconciliation` targets main by no-ff merge.
- All 13 fixed official API probes returned full windows and exact monthly boundary
  OHLC matches. Reused saved responses for offline corrections; no extra API calls.
- Existing backfills: 210 raw rows verify; nine Parquets (183 rows) match raw.
  One older duplicate BTC run lacks its Parquet, so the all-existing-runs gate
  remains FALSE. Its 27 source URL/hash/size records match a verified later run.
- Existing sources cover 153 audited missing keys; combined verified candidates
  cover 534 unique keys, with no conflicts. 32,706 mark symbol-hours remain without
  a verified candidate in this bounded check. No overlay has been integrated.
- WAVES API returns marks after its known settlement: 24 staged rows are labeled
  post-lifecycle context and must NOT restore trading eligibility.
- Latest evidence: `data/interim/usdm_universe/mark_reconciliation_20261117_final/`;
  original 13 API responses remain under `mark_reconciliation_20261117/`.
- Full source report: `docs/MARK_GAP_RECONCILIATION.md`; 30 tests and Ruff pass.

## Prior completed source audit

- Full RAW download completed by the user: 66,893 files, 1,035,606,342 compressed
  bytes; no acquisition errors. No factor backtest or fitting has started.
- Post-acquisition protocol registered on main: `9245a0a`; current audit segment
  `infra/post-acquisition-audit` targets main via no-ff merge. Inspect Git for its
  final merge hash. Raw/canonical datasets were not modified by this audit.
- All 66,893 raw archives independently checksum/size/provenance verified. Exact
  plan/report reconciliation, zero missing/unplanned files, zero integrity errors.
- Missing hourly files: 1,793 boundary-only, 1,180 with interior gaps. Interior gaps
  affect 13 trade files (424 hours) and 1,167 mark files (33,240 hours).
- Four shared mark-gap patterns account for 33,096 symbol-hours. These need source
  reconciliation/backfill, not another full download or blind forward filling.
- 1,913 constant zero-volume trade files across 149 identifiers. Funding files
  start after last observed positive trade activity for 54 identifiers. These are
  ex-post review flags, not inferred delisting dates or causal eligibility rules.
- Interior whole funding-month gaps: BNT (27), BTCST (1), LIT (5), MDT (15).
- Raw superset: 655 current-COIN annotations, 239 current-nonCOIN, 30 absent from
  the current snapshot. Historical product identity remains unresolved in general.
- Official WAVES futures settlement at 2024-06-11 09:00 UTC agrees with the last
  positive-volume bar at 08:00 UTC; later archive rows do not extend tradability.
- Historical eligible universe remains FALSE. 23 tests, Ruff and shell syntax
  checks pass. Full report: `docs/POST_ACQUISITION_AUDIT.md`.

## Relevant artifacts and commands

- Census: `data/interim/usdm_universe/census_full_20261117/`.
- Acquisition: `data/interim/usdm_universe/download_full_20261117/`.
- Audit: `data/interim/usdm_universe/audit_20261117/`; summary, symbol quality,
  exact interior gaps, review rollup, series time bounds and empty integrity errors.
- WSL: `bash scripts/run_usdm_acquisition.sh summary` for compact results;
  `bash scripts/run_usdm_acquisition.sh audit` to reproduce the read-only source audit.
- Reusable audit script: `scripts/audit_usdm_acquisition.py`.
- Shared data lake resides two levels above this repository. WSL execution requires
  escalation in this desktop session; Windows UNC reads work. Python 3.12 stdlib
  tooling works; sibling funding-carry .venv provides Python 3.13 and Ruff.

## Next bounded task

Prepare a resumable missing-key-only mark recovery plan with source evidence,
boundary checks, explicit conflicts and unresolved keys. Integrate a versioned
research overlay only after validation, preserving existing raw/canonical data.
Source lifecycle/identity facts for the 54 funding-after-activity cases and four
funding-gap identities before causal eligibility/accounting rules. No bulk
backfill, canonical integration or strategy performance work was performed here.

## Research and prior evidence

Raw versus residual crypto momentum is a candidate, not a frozen or validated
strategy. Strategy Experiment 001 remains unregistered. The original metadata
lifecycle gate failed and is preserved; the later exact-12-file acquisition pilot
contained only 11 available files and did not satisfy its original count. See
`docs/historical_universe_feasibility.md` and `docs/USDM_ACQUISITION.md` for those
limitations. Acquisition tooling merged at `926ab39` after protocol `6aa2634`.

No push, history rewrite, credentials, real orders, profitability claims,
strategy performance inspection or data deletion.
