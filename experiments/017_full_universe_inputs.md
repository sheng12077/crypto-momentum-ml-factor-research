# Experiment 017: full-catalog chronological universe and factor inputs

Registered2026-11-22before implementation or new factor-panel generation. All
historical years may be inspected for research; none is called a fresh OOS.
This stage creates inputs and a complete repair/assumption queue, not strategy PnL.

## Expectation

Removing the fixed pre2021cohort gate will permit input-ready decision rows for
many identifiers outside the old37. There is no minimum 'passing asset' target:
validity is determined by dated source requirements, not an attractive count.

## Fixed scope and rules

- Account for every identifier in the existing924-entry daily catalog. Preserve all
  raw/canonical data and original prototype contracts/results. No source downloads.
- Process the2021--Oct2026daily release as-is. Do not fabricate2020warmup or join
  early history across an unproven identity bridge. Earlier source integration can
  be independently validated later; insufficient initial history is an explicit state.
- At each next-midnight feature cutoff, use only data from completed prior days.
  Model decision occurs one hour later. Weekly rows use every Monday beforeNov1 2026.
  Momentum20/60/120needs121valid consecutive daily closes within a known source
  episode; gaps/episode changes reset factor history, not financial positions.
- Seven-day imbalance requires7complete valid trade-volume days, positive aggregate
  quote volume, and valid taker-buy bounds. No missing-input zero substitution.
- Funding is observed, not proven paid. Use recorded hourly-event values with a1hour
  availability lag; the7daywindow is defined on availability timestamps, [cutoff-7d,
  cutoff), so hourly-frequency funding is not made impossible by the lag. Require
  sufficient reported-duration coverage, finite values, valid intervals, no gap above
  max adjacent reported intervals+1second, and freshness at the decision cutoff.
- Do not require historical Size/CMCjoins, end-date survival or a fixed pool. Do not
  require all24prior mark hours for price/flow features. Missing valuation/settlement
  marks generate separate repair requirements and never certify execution readiness.
- Retain effective known order stops, partial event days, known equity intervals and
  unresolved regular-execution phase flags as named dated reasons. Unknown lifecycle
  origins are labeled assumptions, not a blanket whole-universe blacklist. Sources
  contain retrospective lifecycle evidence; do not claim certified PIT eligibility.
- Keep separate fields for factor-input readiness, effective scope/phase permission,
  provisional research candidacy and execution readiness. The last remains false in
  this stage. First/last observed activity is not proof of listing/delisting.
- Collect all input-integrity failures and all924dispositions. No first-error silent
  truncation, whole-symbol deletion, future-price gating or fabricated settlement.

## Required outputs

Content-keyed dataset under data/features/full_universe/<build_id>/:
- daily_states.parquet:all catalog IDs x source daily grid, reasons and factor history.
- weekly_candidates.parquet:all catalog IDs x Monday grid, features and reasons.
- asset_summary.csv:all924IDs, first/last observed activity and provisional coverage.
- reason_intervals.parquet:contiguous dated reason/episode/history segments.
- repair_queue.csv:affected intervals, issue type, next action and input provenance.
- decision_counts.csv:dated counts by readiness layer and old-pool membership.
- manifest.json:source/config/code hashes, exact counts, errors and assumption flags.

## Acceptance fixed before execution

1. Exactly the manifest's924IDs accounted; daily and weekly row counts reconcile.
2. No maximum/fixed37restriction; every input file is checksum/identity/date checked.
3. At least one known non-cohort asset with sufficient inputs becomes a provisional
   candidate without Size mapping. Not a target total or proof of tradable validity.
4. Synthetic newly listed, missing-day, reused-episode, hourly funding, lag boundary,
   malformed funding and Size-only restriction examples pass. Future-row mutations
   cannot change earlier features/reasons; corrupt source IDs stay in the output.
5. Funding archive/index/raw-provenance bindings verified before consumption. No
   broad-mark-data eligibility claim from daily diagnostics alone.
6. All source failures and missing-mark/phase issues reported together; no false
   execution-ready, model-fit, PnL or live-readiness flag. Failures may make the build
   incomplete, but do not remove its affected identifiers from accountability.
7. Running from the same inputs/config/financial source gives reproducible tables.
   Reports/READMEare not financial dataset identity inputs. Partial outputs never
   masquerade as a complete build.

No LightGBM fits, portfolio optimization, old OOSgate changes or performance selection
are included. Later full-universe backtests require a separate registered protocol.
