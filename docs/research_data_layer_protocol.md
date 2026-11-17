# Research Data Layer and Lifecycle Review Protocol

Registered: 2026-11-17. User-authorized stages 1 and 2 only. Stage 3 (strategy,
OOS/time splits, selection/fit procedures, performance gates) is explicitly deferred
for discussion. Do not compute returns, rank factors, fit models or pick splits.

## Data layer

Normalize the frozen acquired USD-M archive superset into a NEW versioned data
release: trade/mark hourly observations, funding events, provenance, instrument
identity annotations, lifecycle facts and quality masks. Integrate only the
33,168 verified mark overlay keys; preserve all 72 unresolved keys and the 424
trade-hour gaps. No interpolation, invented volume/funding or overwritten sources.

Preserve exact source numeric strings beside analysis-ready numeric fields. Use
UTC timestamps with explicit open/close/event semantics. Bar-close completion is
only an availability LOWER BOUND, not proof of real-time publication. Funding-event
timestamps retain source subsecond precision and are not assumed to be usable
forecasts or realized payments in inactive contracts.

Use per-file hash-validated, resumable partitions and a dataset manifest. Expose
a read-only loader that does not silently forward fill or treat absent funding as
zero. Keep physical data availability, ex-post lifecycle state, current snapshot
annotations and future strategy eligibility distinct. Unknown historical identity
stays unknown; do not merge renamed/scaled contracts or use current membership
as historical selection. No asset, cost, lookback or volatility target is chosen.

## Lifecycle review

Cover all 924 identifiers in the review ledger, marking unresolved facts honestly.
Prioritize the seven remaining-gap symbols, the 54 funding-after-activity symbols
and the four funding-month-gap identities. Seek official futures announcements for
listing/relisting, new-position restrictions, automatic settlement and migrations.
Spot notices alone cannot establish a perpetual lifecycle. Keep multiple listings
and possible contract episodes for one identifier rather than erasing old history.

Each source fact records URL, source/publication display, retrieval time and hash
where acquired, explicit effective time/timezone, market scope, event type and
whether historical content availability/version is proven. Current-page release
dates are not enough to establish point-in-time availability. The reader must not
silently promote ex-post facts into causal signals or final strategy eligibility.

## Acceptance and handoff

Validate a bounded pilot including BTC, a terminal-event contract and a relisted
contract, then exercise cache-only resume. Check types, row counts, UTC units,
unique event keys, exact mark overlay union, raw-string preservation and explicit
missing-data errors. Full normalization succeeds only when every planned partition
is validated and report totals reconcile. Long execution may be handed off with a
tested command, expected footprint, log/output paths and machine summary.

Deliver reusable code/tests, schema and loader documentation, sourced lifecycle
ledger with coverage/unresolved counts, project status and a discussion checklist
for stage 3 WITHOUT selecting OOS boundaries or a concrete strategy. Publication
of research data does not mean the entire historical trading universe is verified.
