# CMC weekly historical coverage protocol

Registered2026-11-18 before collector implementation and calendar acquisition.
This extends the bounded source audit b863dc2 with a full-calendar DATA acquisition
plan, not a strategy experiment. No factor transformation, labels, fit, return or
OOS-performance inspection; historical size/identity metadata only.

Scope and expectation:
- Frozen range2021-01-01..2026-10-31, matching the observation release. Request
  every Sunday in that interval plus2020-12-27 as a carry-in boundary snapshot.
- Expected calendar305 dates:304 within-range Sundays plus1 carry-in. Source
  listing may be incomplete; reconcile rather than fabricate listed dates.
- Read the public CMC historical index and first public page per date. Existing
  two-date pilot showed200 records/page; record actual counts, never presume
  first-page data cover all coins or every Binance identifier.
- No accounts, credentials, paid endpoints, purchases or access-control bypass.
  One sequential request stream, at least2 seconds between new requests.
  Stop all acquisition on401/402/403/429; save bounded evidence. At most3 attempts
  for transport/5xx failures. Do not hammer blocked resources.
- Explicit256MiB raw-response budget in the handoff command;2MiB response cap.
  Budget includes cached/raw attempt bytes; normalized metadata adds footprint.
  Estimated raw HTML from two-page pilot~150MiB; estimate is not a guarantee.

Acceptance:
- Preserve previous releases/caches. New per-date hashed raw responses, retrieval
  metadata and parsed identity/cap partitions. Bind tool/parser/plan/ledger hashes.
- Pilot fixed at20201227,20210103,20240107,20261025. Validate source date/title,
  unique vendor IDs, positive finite cap, no post-date observations and exact
  decimal representation; retain availability=null and historical-version=false.
- Cache-only resume verifies raw and parsed hashes and needs zero HTTP calls.
- Full date-acquisition gate requires every requested date listed and validated,
  no errors, and exact calendar reconciliation. Variable first-page row counts
  remain explicit; no missing cap/asset/date is inferred as zero or forward filled.
- Deliver coverage by date/vendor ID and review leads for all924 instruments.
  Name/ticker similarities are candidates only, never approved historical mapping.
  Highlight reuse/scaling/index products; do not use current membership as an
  historical selection rule. No strategy universe is selected.
- User may execute the long job after code and bounded pilot validation, with a
  copyable command, budget, expected runtime, log/result paths and success JSON.
- historical_eligible_universe_ready remainsfalse. Final strategy OOS stays sealed;
  paper/live deferred until after OOS review. A free data source is not a proven
  point-in-time vintage, and paid data is not automatically required or sufficient.