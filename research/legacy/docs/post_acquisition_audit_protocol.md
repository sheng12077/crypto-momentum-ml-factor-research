# Post-Acquisition Data Audit Protocol

Registered: 2026-11-17. Data-only audit after acquisition; no signals, strategy
returns, fitting, eligibility optimization or data deletion. Input warning counts
are already known: 2,973 price/mark files with missing hours and 1,913 constant
zero-volume trade files. This is not a blind strategy experiment.

## Scope and fixed checks

- Reconcile all per-file reports against the frozen 66,893-key download plan and
  completed acquisition summary. Require unique keys, exact sizes, SHA-256 fields,
  source URLs, all expected reports and no unplanned reports.
- Re-read every raw ZIP and its official checksum/provenance. Integrity passes
  only with zero missing/corrupt/mismatched sources. Do not overwrite bad evidence.
- Classify hourly gaps as boundary-only or containing interior gaps using the
  reported first/last hour and row count. For every file containing interior gaps,
  inspect raw timestamp rows to enumerate exact missing ranges; do not impute.
- Aggregate data activity by symbol, keeping current non-COIN/unknown annotations
  separate from historical identity facts. Record first/last positive-volume
  trade observations, constant zero-volume files, mark/funding endpoints and
  observations after the last positive-volume trade as audit flags only.
- Current SETTLING status or data inactivity does not prove exact delisting time.
  Full-history activity bounds are ex-post diagnostics, never causal eligibility
  signals. Nonzero funding is not proof of tradability.
- Check the recorded WAVES effective lifecycle event against its raw rows and
  official source. Other event dates remain unresolved without source evidence.

## Outputs and acceptance

Reusable script/tests; ignored JSON summary, per-symbol quality/lifecycle review
queue, interior-gap ranges and integrity errors; committed aggregate report and
updated project handoff. Raw/canonical datasets remain unchanged.

Data-integrity pass requires exact plan reconciliation and zero integrity errors.
Warnings do not disappear on an integrity pass; report their measured distribution
and give a bounded next task. Historical strategy eligibility remains false until
separately specified and sourced. Do not reinterpret partial listing/terminal
months as missing active hours, or automatically delete constant-price series.
