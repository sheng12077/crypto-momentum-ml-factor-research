# Project status

Updated: 2026-11-17.

## Scope and evidence

- Strategy direction under discussion: raw versus residual crypto momentum;
  not frozen, implemented, or performance-tested. Existing BTC/ETH trend drafts
  remain background; strategy Experiment 001 is unregistered.
- Data-only protocol on main: `752b8c1`.
- Current work: `infra/historical-universe-feasibility`; metadata study complete.
- Root discovery and controls pass. Lifecycle gate fails (1 archived-ended pilot
  versus 2 required). No complete historical universe or bulk-download readiness.
- Critical finding: post-delisting archive filenames can persist. Lifecycle
  announcements and row-level evidence must take precedence over directory bounds.
- Evidence: ignored `data/interim/universe_feasibility/20261117_metadata_pilot`.
- Reusable script: `scripts/check_universe_feasibility.py`; five focused tests,
  Ruff and formatting validation. No market ZIPs downloaded; no returns computed.
- Next: separately register and run a tiny lifecycle row pilot, retaining the
  original failed metadata gate. Then decide scope of acquisition.

## Infrastructure

Shared raw/canonical/catalog data lake; sibling funding-carry acquisition, audit,
accounting and paper-journal components. Current inventory is a snapshot, not a
historical universe. Momentum src remains empty. Real-order transport absent.
WSL commands require escalation in this desktop session; Windows UNC file reads
work. Existing funding-carry `.venv/bin/ruff` is available in WSL.

No push, history rewrite, real orders, credentials, or strategy backtests.
