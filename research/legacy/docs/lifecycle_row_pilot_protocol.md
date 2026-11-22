# Lifecycle Row Pilot Protocol

Registered: 2026-11-17, after the completed metadata study. This does not alter
`historical_universe_feasibility_protocol.md` or its failed lifecycle gate.

## Question and expectation

Determine whether archive contents explain filenames persisting after lifecycle
events, and whether the existing public download/checksum/CSV approach can recover
small historical samples. Expect some late archives to contain zero-volume or
constant-price rows. No strategy returns, signals or profitability are computed.

## Frozen samples

- BTCUSDT: trade 2024-05, funding 2024-05 (positive controls).
- WAVESUSDT: trade 2024-05, 2024-06, 2026-10; mark 2026-10; funding 2025-06.
- FTTUSDT: trade 2026-10; funding 2025-06.
- LUNAUSDT: trade 2022-05; mark 2022-06; funding 2022-05.

Use only exact keys from the completed metadata pilot. Download these 12 ZIPs and
their official CHECKSUM files. Limit each compressed ZIP to 1 MiB, combined ZIPs to
4 MiB, each ZIP's uncompressed contents to 10 MiB. Reject unexpected/multiple CSVs,
checksum mismatch, malformed rows, or duplicate timestamps. Never extract paths.
Record raw payloads, provenance, row count, observed time bounds, positive/zero
volume counts, distinct OHLC values and nonzero funding observations. Do not equate
positive volume alone with official tradability or use future samples to select
historical strategies. Zero funding alone does not prove inactive status.

## Fixed decisions

- Transport/parsing is feasible only if all 12 files match their official checksum,
  parse consistently, and both BTC controls have observations (trade control must
  have positive volume).
- A late-file artifact is supported if a post-announcement WAVES trade sample has
  observations but zero positive-volume rows and a constant OHLC value. This is a
  sample-level finding, not a universal terminal detector.
- If no artifact is found, report the discrepancy unresolved; do not change samples
  or thresholds to obtain a pass.
- Even a successful pilot authorizes only a separately scoped acquisition/census;
  full historical-universe completeness, lifecycle resolution, historical margin
  rules, executable depth and strategy profitability remain unproven.

No full backfill, live orders, credentials, or performance inspection.
