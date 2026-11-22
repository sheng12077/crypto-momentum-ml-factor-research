# Completed early-history raw and funding audit

2026-11-19. Preregistered on main at `bc3383a`:
[early_history_audit_protocol.md](early_history_audit_protocol.md).
Tool:`scripts/audit_history_extension.py`. This stage is complete;no user run
needed. No network requests,normalization,returns,fit,PnL or OOS performance.
Original releases,training dates and calendar remain unchanged.

## Independent integrity and gap results

All1526 acquired files/24,153,565 bytes verified against plan/report,official
checksum,size and provenance. Local paths reconstructed under shared raw roots
rather than trusting another host's recorded path. Fresh CSV quality exactly
matches acquisition reports. Full audit47.36s,zero errors. This verifies RAW
integrity,not historical eligibility.

| Hourly bar file classification | Count |
| --- | ---: |
| Complete | 865 |
| Boundary-only truncation | 154 |
| Interior-gap files | 0 |

Trade and mark each have zero detected within-file interior missing hours.
Boundary-only truncation does not establish a launch/settlement date or that all
trading hours are present. Whole absent archive months require separate review.

One constant-price/zero-volume artifact:`LENDUSDT`,November2020,225 hourly rows
from2020-11-01 00:00 to2020-11-10 08:00 UTC;no positive-volume observation. Preserve
these source rows but do not treat them as active trading or fill history from
them. LEND bar-archive monthsNovember/December have no funding archives;this is
not evidence that funding should have been paid in those months.

## Funding observations and unresolved cases

507 funding files,43,027 rows,81 raw identifiers;all reported intervals are8h.
No interval changes;zero stable-interval spacing flags exceeding the registered
1000ms inspection threshold. Maximum within-threshold spacing offset45ms;
timestamps are preserved,not rounded. These spacing checks cannot detect a
missing leading month or prove publication timing/cashflow payment.

- **QTUMUSDT February2020:** trade begins2020-02-20 08:00 UTC;mark begins
  2020-02-19 11:00. No February funding archive in the frozen listing;first funding
  archive observed2020-03-01 00:00. Keep as an unresolved source gap and target
  a separately bounded official API recovery. Never substitute zero fees.
- **DEFIUSDT:**3 funding events without same-hour mark bars:2020-08-27
  08:00:00.010,2020-08-27 16:00:00,2020-08-28 00:00:00 UTC. Observed mark bars
  startAugust28 04:00;positive-volume trade startsAugust28 07:00. These events
  precede available price/activity observations;do not infer live payments or
  invent a prelaunch position. Historical product/episode eligibility needs review.
- No interior funding archive-month gaps between each identifier's first and
  last funding month were found in this window. This does not waive the QTUM
  leading-month gap or LEND boundary mismatches.
- The other43,024 events have a same-hour mark bar in this corpus. A bar's
  presence is not an exact settlement mark price. The three-column funding
  archives do not contain those prices. `funding_cashflows_verified=false` and
  `exact_funding_event_mark_prices_proven=false` remain mandatory.

## Validation and artifacts

141 regression tests pass,including7 new tests for interval/schema checks,
cross-month jitter,spacing versus interval changes,duplicates,host-independent
cache paths,verified resume,corrupt raw data and quality mismatch. New tool/test
Ruff lint/format pass. Native Python3.11 tested;project configured3.13.
BTC/ETH pilot72 files passes2.313s;resume72 hits2.516s.

Ignored root:`data/interim/usdm_universe/early_history_audit_20261119/`:
`full/summary.json`,`gap_files.json`,`funding_review.json`,
`zero_volume_artifacts.json`,per-file checkpoints and separate pilot results.
Log:`reports/acquisition/early_history_audit_full_20261119.log`.
Read summaries with `python scripts/audit_history_extension.py summary`.

Targeted QTUM recovery and DEFI/LEND checks subsequently completed with one
source capture gate unresolved;see [EARLY_CASES_REVIEW.md](EARLY_CASES_REVIEW.md).
Next:versioned early normalization and2019 source-coverage work. Historical
Size,publication/vintage,terminal accounting and final eligible pool remain
unresolved. No claim that the full requested2019 history has been acquired.
