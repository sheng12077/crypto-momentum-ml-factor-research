# Full-catalog chronological inputs — Experiment 017

Registered before implementation in [Experiment 017](../experiments/017_full_universe_inputs.md).
This is an input reconstruction and repair inventory, not a new strategy backtest.

## Scope and result

Every one of the existing catalog's **924 identifiers** is represented on every
source day and every weekly decision date. The previous fixed 37-identifier gate
is absent. No historical Size mapping is required for the three-factor inputs.
The catalog contains contract identifiers, not 924 guaranteed distinct crypto assets.

- Source window: January 2021 through October 2026; earlier files were not silently
  stitched into this release.
- 1,968,120 daily rows; 280,896 weekly rows across 304 Mondays.
- All 924 daily sources and the referenced funding partitions passed source binding,
  checksum, identifier and row checks; zero source-integrity errors.
- 775 identifiers have at least one provisional weekly candidate row, including
  738 outside the previous 37-identifier cohort. This is an ever-qualified count,
  not the number held or available on every date.
- Other dispositions: 133 lack 121 observed days; ten mature after the final weekly
  decision; three need flow/funding review; two have no positive activity in this
  release (GAIB/LEND); PUMP requires regular-execution phase evidence.

| Year | Monday decisions | Minimum candidates | Median | Maximum |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 52 | 0 | 92.5 | 119 |
| 2022 | 52 | 82 | 122 | 137 |
| 2023 | 52 | 136 | 161.5 | 198 |
| 2024 | 53 | 198 | 243 | 265 |
| 2025 | 52 | 269 | 353.5 | 450 |
| 2026 through October | 43 | 137 | 505 | 617 |

Early 2021 zero counts reflect the release's required history warmup. The
2026-06-29 count of 137 is a flagged input anomaly: local funding sources for many
contracts lack the 2026-06-24 04:00 UTC observation. For example, 1000BONKUSDT has
41 instead of 42 four-hour observations in that seven-day availability window.
Adjacent source observations are 00:00 and 08:00 UTC. This proves a gap in the
consumed local series, not whether funding was actually charged or what its value was.
No missing funding value has been fabricated and no threshold relaxed.

## What needs repair

The unclassified queue contains 1,577 **intervals**, not 1,577 assets. Derived review
separates 831 ordinary listing-day flow warmups and four known effective stops.
The remaining **742 review intervals** are:

| Review category | Intervals | Required next action |
| --- | ---: | --- |
| Funding source/evidence | 597 | Check exact event continuity against another official source; preserve absent/unknown values |
| Missing valuation marks | 122 | Locate required trade/mark timestamps before any execution simulation |
| Flow input days | 14 | Inspect the listed underlying trade days and missing hourly inputs |
| Close or episode evidence | 7 | Distinguish missing close, identity change and genuine terminal state |
| Regular-mode transition | 2 | Verify LIT/PUMP phase boundaries before ordinary execution |

Categories overlap in identifiers and time. An interval can affect several decision
dates. The queue is a request for investigation, not proof every item is downloadable.
Normal first-listing warmup remains in the immutable input ledger for provenance;
it does not call for invented pre-listing trades. Unavailable intervals must stay
unavailable, with dated reasons, rather than excluding an otherwise usable identifier
from the whole study.

## Definitions and limits

Features are momentum at 20/60/120 days, seven-day funding sum and seven-day
aggressive-buy/sell quote-volume imbalance. Momentum requires 121 consecutive valid
closes in the source episode; missing closes and episode changes reset feature
history. Flow requires seven complete valid trade days. Funding uses a one-hour
availability assumption, not proven historical publication or payment timestamps.

`factor_inputs_ready`, `research_candidate` and `execution_ready` are distinct.
Execution readiness is **false throughout**. Known dated stops, equity intervals and
regular-mode restrictions remain explicit. Unverified lifecycle origins remain
assumptions. Source checks do not prove complete historical listing/delisting or
point-in-time publication evidence. Missing intraday execution marks are not hidden
by excluding otherwise valid factor observations.

No model, labels, strategy returns or new financial simulation were computed. Old
37-identifier performance remains a restricted prototype result and cannot be
attributed to the expanded population. All previously inspected dates remain
retrospective research, not fresh independent OOS.

## Reproduction and files

Run inside the existing WSL `funding-strategy` environment from the project root:

```bash
conda activate funding-strategy
python -m crypto_factor_research universe --config config/full_universe_inputs.json
# Use the output directory printed above:
python -m crypto_factor_research summary --dataset data/features/full_universe/2a39c4222ec6feaa432e
python -m crypto_factor_research review --dataset data/features/full_universe/2a39c4222ec6feaa432e
```

The optional `--prototype-manifest` on `review` produces the old-cohort comparison;
it never gates candidates. No private API key or new downloads are needed here.
A full build takes a few minutes locally. Success means all identifiers accounted,
zero source errors and the row counts above; it does not mean execution ready.

The financial input content identifier binds source manifests/indices, configuration,
policy, preregistration, input-building code and numerical dependency versions.
Reports and README edits do not invalidate it. Reuse verifies bound sources and
output hashes. Corrupt inputs remain represented in an incomplete build; incomplete
outputs are never reused as a successful final dataset.

- `src/crypto_factor_research/`: new reusable input package, no archived Python imports.
- `config/full_universe_inputs.json`: explicit source window, policy and output root.
- `data/features/full_universe/2a39c4222ec6feaa432e/`: ignored, content-addressed inputs.
- `reports/tables/full_universe_inputs/2a39c4222ec6feaa432e/`: ignored, derived dispositions and review queue.
- `tests/test_full_universe_inputs.py`: chronology, corruption, gap and repair classification tests.

The new stage uses one package and one configuration entry point. Existing prototype
scripts and user working changes are preserved; this stage does not claim the entire
legacy architecture has been migrated.

Next work is targeted source/identity repair and an execution preflight across the
dated candidate population. A full-population model/backtest requires a separate
registered protocol and matched controls. It is not authorized by a passing input
checksum alone.

Final dataset manifest SHA-256:
`5f0ef4bc76d0915d6cd06e99887524a0d5ff33ca152731b1c18fb06bcd1483c4`.
The final build and a complete checksum-verified cache reuse both succeeded.
All 24 active tests pass; package lint passes. Bound paths are local to the shared
WSL lake; generated datasets are not claimed to be portable without remapping.
