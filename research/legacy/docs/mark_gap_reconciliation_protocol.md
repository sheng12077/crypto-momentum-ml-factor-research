# Mark Gap Reconciliation Protocol

Registered: 2026-11-17. Data-only reconciliation; no strategy returns, fitting,
interpolation, bulk backfill, RAW edits or canonical writes.

## Expectation and scope

The completed audit found 33,240 missing interior mark symbol-hours. Four common
patterns account for 33,096: July 24-27 2021, October 2 2022, February 24 2023,
and June 29 2026 (UTC). Existing sibling backfills were designed for funding
timestamps and are expected to cover only a subset of those hourly gaps.

## Fixed checks

1. Validate every manifested `raw/binance_mark_backfill` response: source host/path,
   symbol/interval/time query, acquisition time, byte count, SHA-256, payload time,
   positive finite ordered OHLC, and one-hour close time. Orphaned unmanifested
   responses are counted but not silently reused.
2. Compare each referenced canonical Parquet backfill with the verified raw rows,
   including exact key sets, symbol and OHLC. Do not rewrite either source.
3. Match validated existing rows to exact audited missing symbol-hours. Duplicate
   keys must agree; conflicts are reported and not resolved by averaging.
4. Bounded official API probe: BTCUSDT, ETHUSDT and SOLUSDT for each of the four
   windows, plus WAVESUSDT for June 29 2026 (13 requests maximum). Include one
   observed boundary hour on each side. Validate exact timestamps, OHLC, hourly
   close time and agreement with original monthly boundary rows. Empty, partial,
   error, shifted or conflicting responses remain explicit. No retries to change
   the outcome. All responses are retained with provenance.
5. If needed, allow a bounded official daily-archive fallback for BTCUSDT on
   July 24-27 2021 and the other three dates: at most seven ZIPs plus checksum
   files, 2 MiB per ZIP and 8 MiB combined. Verify checksums and exact daily
   timestamps. Do not extrapolate availability to all symbols from a control.

## Acceptance and outputs

Existing backfill integrity passes only with zero source/provenance/parquet/key
conflicts. Probe recovery is measured separately by exact returned gap hours and
boundary agreement; no fixed rate of recovery is assumed. A failed endpoint does
not invalidate good cached evidence and a control pass does not authorize global
replacement. Record inactive-lifecycle context for WAVES without using returned
marks to extend tradability.

Save ignored validated-candidate rows, manifests, unresolved gap counts and a
compact summary. Commit reusable tooling, focused tests, a reconciliation report
and updated project status. Keep historical eligibility false. Any subsequent
full repair or canonical integration is a separate work segment.
