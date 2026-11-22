# CMC identity and coverage audit protocol

Registered 2026-11-18 before implementation and execution, following acquisition
merge 73e149d. This is a metadata audit, not a strategy experiment.

Expectation: all 305 source/parsed partitions reconcile with the frozen calendar,
collector/parser configuration and lifecycle ledger. Lexical matches will leave
identity and coverage gaps; neither single candidates nor paid data establish
point-in-time eligibility. No target coverage percentage is an acceptance gate.

Acceptance criteria:

- Offline only; no new acquisition, paid access, performance fields, factors,
  labels, model fitting, PnL, universe selection or OOS performance inspection.
- Verify calendar, configuration, ledger, raw response and parsed hashes/counts;
  independently reparse each raw page and reconcile saved mapping review. Stop
  on inconsistency without repairing source artifacts or relaxing checks.
- Report all 305 weekly dates, 924 identifiers and vendor-ID/name/symbol changes.
  Distinguish lexical match counts from approved identity or tradability coverage.
- Per-date archive-month overlap is an EX-POST diagnostic denominator only:
  trade archive first/last month is not a lifecycle, continuous file availability,
  full-month trading evidence or a causal universe. Also report the full 924-ID
  denominator. Never filter by current COIN status or future candidate availability.
- No forward filling, zero caps, symbol-prefix stripping, joining identity
  episodes or automatic mapping approval. Missing first-page entries mean unknown.
- Produce an exhaustive review queue with ambiguity, known reuse, possible
  scaled-contract and noncoin annotation flags; retain dates and exact vendor IDs.
  Each mapping still requires dated exchange/vendor identity evidence, effective
  episode boundaries, units and publication-time/vintage review.
- Historical mappings approved=0, eligible/PIT/all-market readiness=false. Tests
  must catch corrupted raw/parsed/config inputs and missing/ambiguous/censored
  coverage without converting those cases into approved mappings.
- Preserve acquisition outputs. Write derived artifacts to a new version-bound
  ignored directory; commit only reusable tooling, tests and concise findings.

The completed report determines the next evidence-review work; it cannot justify
buying data or excluding instruments from a strategy by future data availability.
