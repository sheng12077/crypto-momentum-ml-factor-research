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
- Next: all-symbol metadata census and sourced lifecycle/identity ledger; then a
  bounded acquisition batch and quality report. Exact total download size/runtime
  are not yet measured. Do not infer trading eligibility from filenames or funding.
- Full findings and acquisition plan: `docs/historical_universe_feasibility.md`.

## Infrastructure

Shared raw/canonical/catalog data lake; sibling funding-carry acquisition, audit,
accounting and paper-journal components. Current inventory is a snapshot, not a
historical universe. Momentum src remains empty. Real-order transport absent.
WSL commands require escalation in this desktop session; Windows UNC file reads
work. Existing funding-carry `.venv/bin/ruff` is available in WSL.

No push, history rewrite, real orders, credentials, or strategy backtests.
