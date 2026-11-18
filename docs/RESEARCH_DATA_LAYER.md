# Research input layer: implementation and execution handoff

Status (2026-11-18): pilot and FULL normalization gates passed. Historical
trading-universe eligibility remains unverified.
Protocol registered on main at f622b1b. Stages 1 and 2 only; strategy/OOS deferred.

## Reproduce or resume the completed conversion

From the repository in a WSL terminal with PyArrow available:

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
python3 scripts/run_research_data.py build
python3 scripts/run_research_data.py summary
```

Use the existing `time-series-momentum` Python environment when needed. This needs
Python and PyArrow, not Codex CLI. The same entry point supports native Windows:
`py -3.11 scripts/run_research_data.py build`. Run ONLY ONE host/writer at a time;
Windows mutex and Linux flock do not interoperate. Stop on any error; retain files.
Re-run the identical command to verify/reuse completed partitions. Do not edit the
builder or replace source inputs halfway through a release: configuration hashes
will reject that. Code/input changes require a new output version.

This is local conversion, with no market-data download, fit, backtest or orders.
There are 66,893 partitions and 35,447,048 expected rows. Runtime/footprint of the
full conversion are not measured; the small sample is not a reliable estimate.
Log: `reports/acquisition/research_build_20261117.log` (append).
Progress is printed every 2,000 partitions. Return the final JSON summary.

Output relative to shared `quant_research/data`:
`canonical/binance_um_research/v20261117_001/`.

Acceptance: exit zero; `success=true`, `full_scope=true`, `errors=[]`,
`verified_partitions=planned_partitions=66893`, `overlay_rows_integrated=33168`,
`overlay_rows_expected=33168`, rows `trade=16217181`, `mark=16418784`,
`funding=2811083`. `historical_eligible_universe_ready` must remain FALSE.
A resumed build may have cache hits. An interrupted run without a successful
manifest is incomplete; do not use it. Existing raw/canonical releases are retained.

## Layout and meaning

- `observations/{trade,mark,funding}/{instrument_id}/{YYYY-MM}.parquet`.
- `index/{sha256(raw_archive_key)}.json`: source/output hashes, counts, time bounds.
- `manifest.json`, `run_config.json`: immutable input/tool binding and build result.
- `lifecycle/{identity_ledger,events,summary}.json`: frozen ex-post review metadata.
- `quality/`: unchanged remaining mark keys and source interior/whole-month gaps.

All numeric prices, volumes and funding rates have their original decimal strings
beside Float64 analysis fields. Timestamps are UTC milliseconds. Trade/mark bars
use open timestamps; close is open+1h-1ms. `available_at_lower_bound=close+1ms`
means the bar cannot be complete earlier; it does NOT establish actual publication
or decision/execution latency. Those assumptions remain for stage 3.

Funding retains exact event timestamp jitter and observed interval, with
`cashflow_validity=unverified_lifecycle`; it is neither a known-in-advance signal
nor proof that an inactive contract paid funding. Missing funding never means zero.
Recovered mark rows retain row-level API/daily provenance and have null volumes
and trade counts. Archive trade/mark volume semantics remain distinct.

Every row retains `historical_strategy_eligible=false`. `month_constant_zero_trade`
is an EX-POST whole-file diagnostic, never a causal filter. Base-row lifecycle
context flags are null (not evaluated); overlay rows retain their earlier audit
flags. Use the attached ledger for evidence; null is not a pass. First/last observed
activity, current membership and nonCOIN annotations are also ex-post context.

## Reader

With `src` installed/on PYTHONPATH:

```python
from datetime import UTC, datetime
from momentum_data import ResearchData

reader = ResearchData('/home/sheng77/working_space/quant_research/data/canonical/binance_um_research/v20261117_001')
bars = reader.bars('BTCUSDT', datetime(2024, 6, 1, tzinfo=UTC), datetime(2024, 6, 2, tzinfo=UTC))
review = reader.lifecycle('BTCUSDT')  # Ex-post facts, NOT tradable membership.
```

Reads use [start,end). Hourly bounds must be hour aligned; no absent partition,
missing hour or duplicate key is silently filled. `require_complete=False` exposes
actual observations for diagnostics only. Known automatic-settlement/underlying-
reuse crossings raise even with that option; request separate episodes.
The reader exposes observations, NOT an eligible portfolio input. It does not yet
reject every row after a terminal event or identify every partial launch hour.
Even a complete hourly grid can contain inactive artifacts. Funding returns only
observed events, without assuming a regular schedule or forecast availability.

## Full release validation (2026-11-18)

User completed the full conversion in WSL using the funding-strategy Conda
environment. Saved manifest and returned summary agree: success/full_scope=true,
66893/66893 partitions, errors=[], cache_hits=0, overlay expected/integrated=33168.
Rows: trade 16217181, mark 16418784, funding 2811083; total 35447048.
Follow-up independently matched current builder SHA and copied lifecycle event/
ledger hashes to the release manifest. Per-partition validation is the completed
builder run evidence; this follow-up did not rescan all partitions. Full-cache
resume is untested and is not required to accept the fresh build result.

## Completed pilot validation

Final pilot `normalization_pilot_004_20261117`: BTC/LIT/WAVES, four sampled months,
34 available partitions, 8,767 trade + 8,768 mark + 960 funding rows, 72 overlay rows.
Fresh build and cache-only resume both passed; 34 cache hits, no errors. Per-file
raw SHA/size, unique keys, expected row counts and exact Arrow/Parquet roundtrip
are checked. Full overlay union is checked by the builder.

Earlier pilot 001 failed one Windows temporary-file rename (33/34). Explicit
Arrow read-handle closure fixed it; pilot 002 passed. Final 004 additionally binds
and includes lifecycle evidence. Failed evidence is retained, not relabeled.
51 unit tests and Ruff pass using native Python 3.11.5/PyArrow 11.0.0. Project
runtime remains Python 3.13; WSL process launches timed out during this session,
so agent-run WSL tests and mypy were not exercised. The user subsequently
completed full WSL normalization as recorded above. No services restarted.

See LIFECYCLE_REVIEW.md for sourced findings and unresolved gates. Full data
conversion and the outstanding lifecycle research are separate from strategy/OOS
registration. Do not proceed to a historical eligible universe on this result alone.