# Experiment 004: development mark-boundary recovery

Registered 2026-11-21 before implementation/execution. No strategy performance,
labels, fitting, OOS analysis, interpolation or source deletion is authorized.

## Expectation and scope

Inventory2021–2022hours with positive observed trade volume and no canonical
mark observation, including month-boundary gaps missed by interior-gap recovery.
Some should be recoverable from official daily mark archives with checksums.
Do not infer a listing, delisting or missing mark from zero-activity placeholders.

## Fixed checks and limits

- Screen924dailyfiles;verify against existing index hashes. Load only2021–2022.
  For affected months verify trade/mark partitions against their recorded hashes
  in the daily source index. Bind daily and hourly inputs in an immutable plan.
- Targets require actual same-hour positive trade volume and missing mark keys.
  Classify leading/trailing/whole-month/interior gaps; never replace existing keys.
- Pilot:BTCUSDT2022-07-31,then bounded full acquisition when workload is modest;
  otherwise provide a resumable full command after pilot validation. No keys.
- Public source:data.binance.vision official daily USD-MmarkPriceKlines1hZIP
  and matching CHECKSUM. Verify SHA256, ZIP member/name/decompressed size, exact
  UTCday/hour/open/close timestamps, duplicate/order constraints and finite positive
  validOHLC. Reuse existing validated parser/fetcher without editing frozen tools.
- Compare every overlapping same-day canonical mark against official daily OHLC
  with exact decimals. Any conflict prevents that source-day from entering overlay.
  Entire missing days rely on official archive+checksum provenance; do not pretend
  an overlap check exists when there are no overlapping rows.
- Pace requests globally at>=1second;maximum500source-days,1000HTTPrequests,
  64MiBcompressed total,2MiBperZIP,10MiBdecompressed. Bound HTTP timeouts;
  stop on403/418/429. Persist failures and do not blindly retry absent source-days.
  Resume only failed transport attempts or explicitly requested terminal retries;
  always verify cached successful bytes/checksum before reuse.
- Export a NEW versioned Parquet overlay with exact decimal strings, UTCms,
  source URL/hash/retrieval/cachepath. Validate exact recovered/remaining target
  partition, unique keys and numeric/string equality after Parquet readback.
  Never overwrite original or old recovery data;trading eligibility staysfalse.
- Acceptance:zero integrity/conflict errors and exact provenance/readback checks.
  Full recovery means every planned target found;missing/404/partial sources
  remain explicit and prevent full-recovery claims. Do not revise this threshold.
- Replay must make zeroHTTPrequests for cached successes and reproduce identical
  overlay data/hash. Record source counts, bytes, coverage and unresolved keys.

## Deliverable

Reusable inventory/resumable acquisition/export tool, tests, pilot evidence and
full result or copyable bounded full command with log/output/success criteria.
This overlay alone does not rebuild daily research inputs, approve identities,
or make the learned strategy ready for historical simulation.
