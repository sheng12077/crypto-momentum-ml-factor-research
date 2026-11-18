# Daily episode-aware research-input protocol

Registered 2026-11-18 before implementation/execution, based on fcfcacf. User
authorizes daily qualification and a NEW research-input version; strategy/OOS
split discussion is explicitly deferred. No returns, factors, labels, fits, PnL,
orders, performance inspection, paper/live execution or source replacement.

Scope: entire924-ID ledger, observations2021-01-01..2026-10-31. Retain raw data
and valid periods. Read the immutable normalized observations, reviewed events,
negative gates and CMC sources. Publish daily derived sidecars, not a rewrite of
the old release. No new acquisition or paid access.

Fixed technical diagnostics (not optimized strategy settings):

- Data day is UTC; reference time is next00:00UTC, an availability LOWER BOUND,
  not proven publication time or a chosen execution/rebalance schedule.
- Validate hourly keys/finite fields; count complete24-hour trade/mark days.
  Aggregate observed close/volume/taker sums only; no momentum or imbalance ratio.
- Track daily close endpoints20/60/120 days back and121 consecutive daily closes
  for120 daily intervals. Never confuse elapsed time with valid closes. Expose
  endpoint versus complete-history diagnostics separately. Do not fill gaps.
- Reset history on known launches/relaunches/underlying changes; do not connect
  identities through a reused symbol. Flag partial lifecycle days; respect known
  settlements/new-position stops and reviewed scoped restrictions. Unknown initial
  boundaries and current classification stay explicitly unresolved.
- Funding uses only observations with ORIGINAL timestamp strictly before the
  reference time and inside the same episode. Preserve jitter and reported
  interval. Report event age and freshness within that last reported interval as
  a diagnostic; observed rates do not certify paid funding or exact cashflows.
- Strict Size availability remains unproven where available_at=null. Separately
  expose a fixed research assumption: snapshot day end+7 calendar days, valid for
  exactly7 days. No unbounded carry-forward, cross-ID splice, cap rescaling or
  borrowing a future observation. Publication/revision vintage is NOT proven by
  this lag. This does not freeze the final strategy's lag/decision-time rules.
- Use only reviewed overrides/episode proposals or literal single-ID review leads;
  ambiguous/missing/blocked mappings remain unavailable. No automatic historical
  mapping/trading approval. Explicit equity episodes cannot become crypto inputs.
- BNX legacy February source: checksum/hash validate, integrate only original
  hours before2023-02-11 04UTC, reject conflicts. Expect244 source hours in the
  full window;267 post-close rows remain excluded. Preserve per-source provenance
  and old canonical release. Mark the old 'not integrated' restriction satisfied
  only when this version actually verifies/consumes the recovered244 hours.

Acceptance:

- Bind source plan/release/index/Parquet hashes, latest reviewed ledger/policies,
  full-screen cohorts and CMC partitions. Atomic per-identifier output and verified
  resume; changed config/tool requires a new version. No silently unmanifested
  partitions, conflicting duplicates or source repair.
- Per-day output includes technical candidate flags and exclusion reasons;
  separate price/funding candidates, assumed-Size candidates and strict proof
  gates. All formal historical eligibility/PIT certification stays false until
  unresolved identity/lifecycle/publication/funding gates are addressed.
- Synthetic tests cover missing closes,121-point history, episode resets, launch/
  closure boundaries, strict funding timestamps/jitter, bounded Size validity,
  incomplete days, legacy conflicts and source/checkpoint corruption.
- Fixed real pilot: BTC2023-01..05;BNX2023-01..06;PUMP2025-04..08;
  LIT2025-12..2026-03;SUN2024-08..12. Load up to120 prior calendar days where
  acquired; no invented pre-2021 history. Verify resume and compact summary.
- Prepare full build over all924 IDs, daily counts/reason reports and reproducible
  commands/logs. Execute if modest after measurement; otherwise hand off the long
  build in user's existing Conda environment after implementation/pilot validation.
- Do not choose or disclose a final OOS split. No strategy performance selection.
