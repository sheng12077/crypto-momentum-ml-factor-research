# Post-Acquisition Quality Audit

Date: 2026-11-17. Protocol registered on main as `9245a0a` before this audit.
No strategy returns, models, backtests, data deletion or backfills were performed.

## Decision

RAW integrity passes. The data are suitable for further normalization and repair,
but NOT yet a historical eligible factor universe. Source anomalies and unresolved
contract lifecycles must remain explicit. Do not rerun the full download merely
because these source-quality warnings exist.

## Independent integrity verification

- Exact reconciliation: 66,893 planned keys, 66,893 reports, no missing/unplanned
  reports. Recorded total equals the plan: 1,035,606,342 compressed bytes.
- Re-read every raw ZIP, compare the official checksum, listed size, report hash,
  source URL and persisted provenance. Zero integrity errors.
- Aggregate the previously parsed row-quality reports. Independently read timestamp
  rows for every price/mark file with interior gaps and reconcile exact gap ranges.
  This audit does not claim to independently reparse every OHLC/funding field twice.

| Dataset | Files | Parsed rows | Boundary-only gap files | Interior-gap files |
|---|---:|---:|---:|---:|
| Trade 1h | 22,635 | 16,217,181 | 964 | 13 |
| Mark 1h | 22,905 | 16,385,616 | 829 | 1,167 |
| Funding events | 21,353 | 2,811,083 | n/a | not assessed as fixed-hour bars |

Of 2,973 hourly files flagged during acquisition, 1,793 have missing rows only at
month boundaries; 1,180 contain interior gaps (some also have boundary gaps).
Boundary-only means partial observed month, not a proven listing/delisting cause.
42,567 hourly files are complete. Funding gaps cannot be assessed using an assumed
constant eight-hour schedule; interval changes and lifecycle facts need separate work.

## Interior gaps

Trade contains 424 missing interior hours in 13 files across 11 identifiers:
AERGO, AIA, BNX (three months), CTK, CVC, CVX, LIT, MAVIA, MDT, PUMP and SLP.
MDTUSDT 2026-10 is the largest trade gap, at 201 hours. These may represent source
gaps or contract lifecycle interruptions; do not automatically interpolate prices.

Mark contains 33,240 missing interior hours. Four exact shared patterns account
for 33,096 of these symbol-hours:

| Missing UTC interval | Hours per symbol | Affected identifiers |
|---|---:|---:|
| 2021-07-24 00:00 through 2021-07-27 23:00 | 96 | 74 |
| 2022-10-02 00:00 through 23:00 | 24 | 151 |
| 2023-02-24 00:00 through 23:00 | 24 | 170 |
| 2026-06-29 00:00 through 23:00 | 24 | 762 |

These are shared archive gaps, not proof that trading stopped at the exchange.
Prior sibling canonical data may contain separately sourced API backfills; those
must be reconciled by timestamp and provenance rather than overwriting RAW evidence.
Mark gaps materially limit defensible liquidation/margin simulation.

## Inactive-data and lifecycle review

- 1,913 constant, zero-volume trade files across 149 identifiers. This is an
  inactivity/artifact flag, not a universal delisting detector.
- 54 identifiers have funding files beginning after their last observed
  positive-volume trade bar. These are review candidates, not automatically
  impossible payments or proof of a lifecycle date. Do not book them blindly.
- The raw superset comprises 655 identifiers currently labeled COIN, 239 currently
  labeled non-COIN, and 30 absent from the current snapshot. These labels are
  discovery-time annotations and do not establish historical classification.
- Even among the 655 current-COIN identifiers: 136 have constant zero-volume trade
  files; 37 have funding files after their last positive-volume trade observation.
- GAIBUSDT and LENDUSDT have no positive-volume trade observation in this window;
  retain the missing-data facts rather than assuming an investable history.

Whole interior funding-month gaps appear for BNTUSDT (27 months), BTCSTUSDT
(one month), LITUSDT (five months) and MDTUSDT (15 months): 48 symbol-months total.
Trade and mark have no whole interior monthly archive gaps. Missing funding may
reflect lifecycle interruptions/identity reuse, not necessarily a recoverable
download omission; never fill it with zero.

The official [WAVES announcement](https://www.binance.com/en/support/announcement/detail/f65faeeefe07417a8b6dd2900ba8da7e)
sets the futures settlement at 2024-06-11 09:00 UTC and prohibits new positions
from 08:30 UTC. The last positive-volume trade bar starts at 08:00 UTC, consistent
with that boundary. Its subsequent constant trade files and later funding records
must not extend tradability. The same notice distinguishes spot removals from
perpetuals that continue trading (OMG/XEM), so spot delisting must not be applied
to all derivatives. The page's current publication display is not a verified
as-of timestamp/version; `announcement_available_at` remains unresolved.

All activity endpoints above use full-history information for diagnostics only.
They must NOT be used to retroactively select winners, drop an asset's early
history, or build a causal trading rule.

## Artifacts and reproduction

Ignored output: `data/interim/usdm_universe/audit_20261117/`:

- `summary.json`: integrity, reconciliation and aggregate counts.
- `integrity_errors.json`: empty.
- `symbol_quality.json`: per-identifier activity and lifecycle-review queue.
- `interior_gaps.json`: exact missing timestamp ranges.
- `review_rollup.json`: current-label diagnostics, common patterns and whole-month gaps.
- `series_observed_bounds.json`: first/last reported trade, mark and funding observations.

Run from this repository in WSL:

```bash
bash scripts/run_usdm_acquisition.sh audit
bash scripts/run_usdm_acquisition.sh summary
```

Log: `reports/acquisition/audit_20261117.log`. The source audit takes minutes locally;
it reads the approximately one-GiB corpus and many small provenance files, with no
network calls. Success requires exit zero, `success: true`,
`verified_raw_files: 66893`, `integrity_error_count: 0`, and empty reconciliation
missing/unplanned lists. Eligibility remains false even when integrity passes.
23 focused tests and Ruff checks pass.

## Recommended next bounded task

Prepare normalized research tables with explicit quality masks; reconcile the
four common mark-gap patterns against existing separately sourced backfills and
test a small official backfill where necessary. In parallel, prioritize the 54
funding-after-activity cases, four funding-month-gap identities and symbol migrations
for sourced lifecycle review. Do not repair all 924 identities by guessing, forward
fill execution prices, or start factor fitting before eligibility/accounting rules
are separately fixed. No repair/backfill was performed in this audit.
