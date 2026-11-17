# Project status

Updated: 2026-11-17.

## Scope and evidence

- Strategy direction under discussion: raw versus residual crypto momentum;
  not frozen, implemented, or performance-tested. Existing BTC/ETH trend drafts
  remain background; strategy Experiment 001 is unregistered.
- Data-only protocol on main: `752b8c1`; metadata tooling commit `761d545`.
- Row-pilot protocol on main: `96ed53b`.
- Completed work targets main via `infra/lifecycle-row-pilot` merge; inspect Git
  for the final merge hash. Metadata and bounded row feasibility are concluded.
- Root discovery and controls pass. Lifecycle gate fails (1 archived-ended pilot
  versus 2 required). No complete historical universe or bulk-download readiness.
- Critical finding: post-delisting archive filenames can persist. Lifecycle
  announcements and row-level evidence must take precedence over directory bounds.
- Evidence: ignored `data/interim/universe_feasibility/20261117_metadata_pilot`.
- Follow-up evidence: ignored `data/interim/universe_feasibility/20261117_lifecycle_rows`.
  All 12 tiny ZIPs checksum-verified (123,510 bytes). Late WAVES/FTT trade samples
  contain only zero-volume constant-price rows; nonzero late funding still exists.
  Row transport/parsing and sample artifact tests pass. Original metadata gate fails.
- Reusable scripts: `scripts/check_universe_feasibility.py` and
  `scripts/check_lifecycle_rows.py`; nine focused tests, Ruff and formatting pass.
  No bulk acquisition or returns computed. Full-download readiness is false.
- Acquisition protocol on main: `6aa2634`; current segment `infra/universe-acquisition`
  targets main via no-ff merge. Check Git for its final merge hash.
- Full metadata census completed: 924 USDT identifiers, 2,772 jobs, no errors;
  66,893 checksum-bearing ZIPs, 1,035,606,342 compressed bytes (0.9645 GiB).
  Current metadata labels 239 non-COIN products; 30 lack a current record.
  These are annotations of a RAW superset, not a crypto eligibility screen.
- Full census: `data/interim/usdm_universe/census_full_20261117/`; `identity_ledger.json`
  preserves unknown lifecycle facts and current snapshot provenance. Only a sourced
  WAVES event is currently recorded; no complete historical lifecycle ledger yet.
- Small census/acquisition/resume verified. Registered 12-file sample premise was
  incorrect: WAVES funding 2026-10 is missing, leaving 11 files. Exact-count gate
  remains unsatisfied. All available files verified; second run was 11 cache hits,
  zero downloads. Do not fabricate missing funding or claim exact protocol pass.
- 18 tests, Ruff and shell syntax validation; no strategy performance inspected.
- USER HANDOFF: full ZIP download has NOT started. Copy-ready command, measured
  budget, output/log paths and success criteria: `docs/USDM_ACQUISITION.md`.
  Run `USDM_MAX_GIB=1.1 bash scripts/run_usdm_acquisition.sh download` in WSL.
- Next after download: inspect summary, resolve historical identity/lifecycle and
  normalize/audit canonical data before defining strategy eligibility or returns.
- Full findings and acquisition plan: `docs/historical_universe_feasibility.md`.

## Infrastructure

Shared raw/canonical/catalog data lake; sibling funding-carry acquisition, audit,
accounting and paper-journal components. Current inventory is a snapshot, not a
historical universe. Momentum src remains empty. Real-order transport absent.
WSL commands require escalation in this desktop session; Windows UNC file reads
work. Existing funding-carry `.venv/bin/ruff` is available in WSL.

No push, history rewrite, real orders, credentials, or strategy backtests.
