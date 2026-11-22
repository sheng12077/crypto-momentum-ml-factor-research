# Historical USD-M Metadata Census and Raw Acquisition Protocol

Registered: 2026-11-17. Data engineering only. No strategy returns, fitting,
parameter tuning, performance inspection or trading. Prior feasibility decisions
remain unchanged. Strategy Experiment 001 is still unregistered.

## Frozen scope

Use the saved 20261117 metadata root census as the source population, including
every discovered identifier ending in USDT from trade, mark or funding roots.
Include Unicode/scaled identifiers, discontinued markets, incomplete histories
and unresolved product identities. Do not intersect with today's exchangeInfo.
Window: 2021-01 through 2026-10. Trade/mark interval: 1h. Spot is not required.
The population is an archive-discovered raw-data superset, not an eligible crypto
perpetual universe. Current product metadata is an annotation only.

## Metadata census

List exact per-symbol trade, mark and funding keys with complete pagination.
Persist response provenance/hashes, checksum-object availability, file sizes,
month coverage, interior gaps and three-series overlap. Save each job separately
for validated resume. Produce a coverage table, raw-download plan, identity ledger
and summary. Preserve known WAVES delisting evidence and its publication/effective
time distinction; all unsourced identity/lifecycle facts remain unresolved.

## Bounded validation before handoff

Run a small census over BTCUSDT, ETHUSDT, LUNAUSDT and WAVESUSDT. Exercise the
download tool using BTCUSDT and WAVESUSDT, months 2024-05 and 2026-10 (12 files).
Budget: 4 MiB compressed. Re-run the same download and require checksum-verified
cache hits rather than new downloads. Inspect structural row quality and artifact
flags, not profitability. Test failed integrity, pagination and date filtering.

## Acquisition rules

- Full metadata census has no market ZIP downloads. Long runs may be handed to
  the user with a tested command, logs, output paths and machine summary.
- Raw download requires a complete census plan, official checksum for every
  planned file, and an explicit compressed-byte budget. Missing series are reported
  and preserved as missing; never synthesize zero funding or tradability.
- Verify official SHA-256 and listed size before CSV parsing. Retain source URL,
  acquisition time, checksum and provenance. Reuse sibling caches only after full
  integrity/provenance verification. Never overwrite another strategy's canonical
  datasets. Raw ZIPs remain ignored in the shared data lake.
- Use bounded concurrency (default 4), per-response size caps and safe in-memory
  ZIP reads. No extraction paths, API keys, orders or unbounded retries.
- Report duplicate/unordered timestamps, malformed/non-finite rows, OHLC violations,
  out-of-month observations, coverage and zero-volume/constant-price anomalies.
  Mark-price volume is not trading volume. Zero funding is not automatically invalid.
- Success means complete, checksum-verified RAW acquisition and recorded structural
  quality; it does not mean trading eligibility, clean factor inputs or live readiness.
- Any network/integrity failure remains explicit with a nonzero exit and summary;
  rerunning verifies successful cached work and retries remaining failed jobs.

## Acceptance and next stage

Tooling passes when focused tests, lint, small census, 12-file acquisition and
verified cache-resume check pass. Full census is complete only with no failed
listing jobs; report measured file count and bytes before bulk download.
Full-universe identity/lifecycle resolution and strategy eligibility are separate
work. Do not drop an asset's early history based on its future delisting. Factor
research requires a separately registered protocol and point-in-time accounting.
