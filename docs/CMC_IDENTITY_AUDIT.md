# Weekly cap identity and coverage audit

Registered on main at b9771a3 before implementation. Acquisition merge 73e149d
is unchanged. This audit reads the completed local source cache only; no HTTP,
paid access, strategy universe, factors, labels, models or OOS performance.

## Reproduce

From the repository in the existing environment:

```bash
conda activate funding-strategy
python scripts/audit_cmc_identity.py
```

No additional dependencies. Default inputs are
data/interim/cmc_weekly_20261118/ and
data/interim/usdm_universe/lifecycle_review_20261118/.
Derived artifacts are under data/interim/cmc_identity_audit_002_20261118/ (ignored).
The audit rechecks the entire cache, so it may take several minutes over a
Windows/WSL shared filesystem. It does not repeat downloads. A mismatch exits
nonzero and leaves source files untouched; inspect the traceback rather than
editing evidence. Only one writer/host at a time.

The source calendar, collector/parser configuration, ledger, all raw bytes,
parsed hashes/counts and fresh metadata-only raw parses must agree. Original
mapping/date/vendor coverage reports are independently regenerated and compared.
Derived outputs bind those input hashes and the audit script hash; a deliberate
tool/input revision needs a new --output directory. Missing first-page entries
are never zero filled or forward filled.

## Outputs and interpretation

- summary.json: reconciliation outcome and readiness gates.
- weekly_lexical_coverage.json: same-date literal symbol match counts, separately
  for all 924 IDs and IDs whose first/last trade archive month spans that date.
- yearly_lexical_coverage.json: sums of the latter instrument-week diagnostics.
  The 2020 row is the single carry-in date, not a full year.
- identity_review_queue.json: all 924 identifiers, exact vendor IDs and dates,
  overlapping-month gaps, risk flags, evidence checklist and empty approvals.
- vendor_identity_history.json: vendor IDs with dated symbol/name/slug labels;
  changes are review leads, not proof of identity continuity or a migration ratio.

The archive-month denominator is ex-post and approximate. It includes incomplete
listing/delisting months and may span missing files, inactive intervals and reused
symbols. Current baseAsset is a lexical annotation, not historical underlying
evidence. Neither denominator is a point-in-time tradable universe. Multiple
candidate IDs across history need not coexist on the same date; a single
same-date candidate still requires episode-specific verification.

## Completed findings

Version002 completed successfully:305 dates,61,000 fresh-parsed rows,662 vendor
IDs and924 instruments;zero reconciliation errors. Acquisition summary SHA256:
7c05562334962f8e2b356b058a8798ed89cfed023c3d8cfb98d8856ef336ef1e.
Audit script SHA256:
d2428b5cd4a1fcadbfd207c2d2beac2b70dc9cf6eb293240ad009e6fc91566ed.

- 418 instruments have at least one literal candidate somewhere in the full
  calendar;506 have none. This is NOT time-specific identity coverage.
- 9 multi-ID histories,3 known reused identifiers,16 possible scaled contracts,
  239 current noncoin annotations. Flags overlap; none define a historical pool.
- 2 IDs have missing trade archive bounds (GAIBUSDT,LENDUSDT), so remain in the
  full924 denominator but are flagged outside the archive-month denominator.
- 23 vendor IDs have multiple raw symbol spellings, including case-only variants.
  Examples in the captured data:1414 FIRO/XZC,5690 RENDER/RNDR,4172 LUNA/LUNC,
  23635 BNX/FORM. These observations do not verify futures continuity, migration
  dates/ratios or vendor content vintage.
- All61,000 rows retain unproven publication availability/content vintage.

The following diagnostic sums same-date literal matches over instrument-weeks
inside ex-post trade archive month spans; counts are not approved Size coverage:

| Year | Weeks | Instrument-weeks | Literal matches | Absent/unknown | Match % |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 52 | 6,073 | 4,863 | 1,210 | 80.1 |
| 2022 | 52 | 7,613 | 5,393 | 2,220 | 70.8 |
| 2023 | 53 | 10,770 | 6,864 | 3,906 | 63.7 |
| 2024 | 52 | 15,643 | 7,603 | 8,040 | 48.6 |
| 2025 | 52 | 25,946 | 7,816 | 18,130 | 30.1 |
| 2026 through October | 43 | 32,025 | 6,628 | 25,397 | 20.7 |

This decline conflates first-page censoring, different asset identities/labels,
scaled instruments and changing product composition including noncrypto products.
It is not a crypto-only coverage estimate or a quantified paid-data requirement.
No current noncoin filter or future-availability filter has been applied.

## Review procedure

1. Start with the nine multi-ID candidates (BNX, BTCST, BTT, DYDX, KNC, LIT,
   LUNA, STRK, SUN), known reused LIT/PUMP/MDT and flagged scaled contracts.
   Some groups overlap. Do not strip contract prefixes to manufacture matches.
2. For each contract episode record exchange launch/closure and underlying,
   official vendor ID/chain/contract identity, migration dates and ratios, exact
   source URLs, retrieval hashes, evidence publication time and unresolved items.
   Spot token migration announcements alone do not establish futures continuity.
3. Record mappings with explicit effective_from/effective_to, unit convention,
   evidence and reviewer decision in a separate reviewed artifact. Never edit
   the generated queue or the original acquisition to appear approved.
4. Only then measure Size availability inside a separately justified historical
   universe. First-page omissions are censored/unknown. An ID absent all year may
   be below page coverage, renamed, scaled, noncrypto or genuinely unmatched.
5. Evaluate paid data against the measured asset/date/vintage deficit. Neither
   top-200 complete dates nor a paid daily feed proves historical publication
   timing. An assumed one-week lag would not prove unrevised content either.

## Validation

77 unit tests pass, including six new audit tests (six corruption subcases),
offline run/resume, raw/parsed/config/ledger/mapping/summary tampering, a rehashed
parsed change rejected by independent raw parsing, same-date coverage without
future candidate borrowing, missing/null archive months and no automatic approval
of known reuse. The initial full audit verified source/parsed evidence but failed
on null archive-month bounds during aggregation. That attempt's configuration is
preserved in cmc_identity_audit_20261118/. Version002 treats missing bounds as
unknown and flags exclusion from the overlap denominator, retaining all IDs in
the all-identifier denominator. Source inputs were not changed.
New script/test Ruff lint and formatting pass. Unchanged full-tree native lint
issue in test_research_data.py remains recorded in PROJECT_STATUS.md.
Validated with native Python 3.11; configured project runtime is Python 3.13.

No historical mappings approved; historical eligibility, PIT and all-market
coverage remain false. Simulation and final OOS inspection remain deferred.
