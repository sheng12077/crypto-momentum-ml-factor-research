# Daily episode-aware research inputs

Implementation: `scripts/build_daily_inputs.py` and `scripts/daily_input_rules.py`.
Preregistration: [daily_inputs_protocol.md](daily_inputs_protocol.md), committed
on main at `93cf6e1` before implementation. No strategy performance inspected.

## What this build produces

New daily Parquet sidecars retain every ledger identifier and attach row-level
failure reasons. The existing hourly canonical release remains unchanged. Each
output binds source Parquet/index/acquisition-report hashes, lifecycle evidence,
identity policy, market-cap partitions and builder dependencies. Resume verifies
those bindings and output hashes; conflicting inputs fail closed.

- A UTC data day has 24 expected trade and mark hours. Next midnight is only a
  reference/availability lower bound, not a chosen execution time or latency.
- Raw closes, volume, taker-buy totals and observed funding are retained. There
  are no momentum returns, imbalance ratios, targets, model fits or PnL.
- Valid 20/60/120-day endpoints and 121 consecutive valid closes are separate
  diagnostics. The latter covers 120 return intervals. Missing/zero-activity
  closes and known new episodes reset continuous history; no forward filling.
- Known launch, settlement, order-stop, partial-day and scoped identity
  restrictions are attached. Unknown lifecycle boundaries remain unresolved;
  retaining a row is not historical trading approval.
- Funding must precede the reference time and belong to the same episode.
  Timestamp jitter is preserved. A freshness diagnostic uses the last reported
  interval; this does not establish cashflow payment or settlement accounting.
- Historical Size publication time and revision vintage remain unproven. Strict
  Size eligibility therefore stays false. A separately labelled diagnostic uses
  snapshot-day-end plus seven days, expiring seven days later. This is a research
  assumption, not proof against look-ahead bias or a frozen strategy parameter.
  Missing/ambiguous/blocked mappings are unavailable; vendor IDs are not spliced.
- Current asset classifications remain ex-post review annotations. The optional
  class-review-clear count is not a causal universe definition. Explicitly known
  equity episodes are blocked from crypto-input candidates.

The new sidecar integrates the 244 verified pre-settlement legacy BNX hours from
the cached February 2023 archive. Its 267 post-close hours are excluded. Only
verified integration lifts the old conditional legacy restriction here; old
releases and audit results remain intact.

## Completed checks

Fixed pilot: BTC, BNX, PUMP, LIT and SUN in the preregistered windows. It produced
759 daily rows, verified 102 source partitions and consumed all 244 legacy BNX
hours, with zero errors. Initial build: 17.328 seconds; verified resume: 11.031
seconds and five cache hits on native Windows Python 3.11 / Arrow 11. These are
pilot timings, not a prediction of full WSL runtime.

Three identifiers passed the price/funding diagnostic at least once; two passed
the four-factor assumed-Size diagnostic. Strict eligibility stayed zero. These
are limited pilot diagnostics, not full-universe asset counts.

All 111 regression tests passed. The three new Python files passed Ruff lint and
format checks. The configured project runtime is Python 3.13; validation used
the available native Python 3.11. Full daily conversion has **not** run.

## Full build in WSL

From the momentum_strategy repository directory:

```bash
conda activate funding-strategy
python scripts/build_daily_inputs.py full --workers 2
python scripts/build_daily_inputs.py summary
```

This reads existing local data; no new downloads or paid data are required.
Runtime is not yet measured. It reads/verifies 66,893 source partitions and
writes daily sidecars for 924 identifiers. Run only one writer, on one host.
If interrupted, rerun the same build command with unchanged code/inputs.

Log: `reports/acquisition/daily_inputs_full_20261118.log`.
Full output: shared data root
`canonical/binance_um_daily_research/v20261118_001/`, including `daily/`,
`index/`, `daily_counts.json`, `reason_counts.json` and `manifest.json`.
Pilot output: `data/interim/daily_research_pilot_20261118/`.

Expected successful full manifest:

```json
{
  "success": true,
  "errors": [],
  "full_scope": true,
  "identifiers": 924,
  "daily_rows": 1968120,
  "source_partitions_verified": 66893,
  "legacy_BNX_hours_consumed": 244,
  "historical_eligible_universe_ready": false,
  "strict_Size_publication_vintage_proven": false,
  "strategy_and_OOS_decisions": "deferred_by_user",
  "OOS_performance_inspected": false
}
```

Daily rows include unlisted/blocked/missing periods with reasons, not 924 usable
assets every day. Candidate counts are measured by the build, not prescribed.
Readiness flags remaining false are expected unresolved research gates.

After the full manifest is checked, discuss chronological train/validation/OOS
splits and label overlap, then freeze strategy/model/turnover/cost protocols
before performance experiments. No split was selected by this build.
