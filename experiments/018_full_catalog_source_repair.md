# Experiment 018: full-catalog source verification and targeted repair

Registered 2026-11-22 before implementation or source requests for this stage.
No strategy labels, model fitting or PnL are included. Historical research is retrospective.

## Expectation

A single resumable pass can account for every pending Experiment017 review interval,
reuse validated local recovery payloads, and recover some missing observations from
official public sources. No minimum recovery count is required. Public availability
and completeness are unknown until tested; no paid source or private credential is used.

## Fixed rules

- Input: full-catalog dataset2a39c4222ec6feaa432e and its hash-verified reviewed queue.
- Account for all742pending intervals, and preserve831listing warmups/four known stops.
- Expand flow/mark/close gaps to exact source days or timestamps. Funding gap evidence
  uses recorded adjacent events and their stated intervals, not an assumed global8hclock.
- Prefer verified local recovery caches, then official public REST/daily archives.
  Rate-limit requests, bound retries/timeouts, honor rate-limit responses and save raw
  responses/URLs/retrieval timestamps/hashes. An access denial is not proof of absent data.
- Validate symbol/time/schema, finite positive prices and volume bounds. Check overlap
  conflicts against the consumed source. Never overwrite original canonical releases.
- Missing funding values are never inferred, zero-filled or interpolated. Report
  frequency-change/terminal uncertainties separately from recoverable missing rows.
- Save validated observations as a source-bound additive repair overlay; source
  conflicts are blockers, never silently replaced. Absence/HTTP/access errors remain
  named dated unresolved dispositions. Terminal/phase evidence must retain its scope.
- Resolve every interval as recovered, already covered, expected state, or explicitly
  unresolved with evidence and next action. Produce a complete summary even if some
  requests fail. Source integrity alone never certifies execution or PIT readiness.
- The pass does not declare full simulation readiness. Expanded execution preflight
  must separately verify required valuation/fill/funding/terminal timestamps before PnL.

## Acceptance

1. Every original review interval has a stable key and terminal disposition in a
   machine-readable report; no first-error truncation or whole-asset removal.
2. Synthetic valid/invalid/missing/conflicting response and resume tests pass.
3. Cache reuse checks hashes and query identity; no unverified old payload accepted.
4. Downloads are bounded to explicit missing-data jobs, with request/error counts.
5. All remaining limitations are listed, not converted into success or fabricated data.
