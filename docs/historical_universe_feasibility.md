# Historical Universe Feasibility

## Metadata pilot: 2026-11-17

Decision: root discovery and controls pass, but the registered lifecycle gate
does not pass. Only LUNAUSDT meets the archive-ended definition; the required
count was two. Do not change that threshold or infer full acquisition readiness.
No strategy performance was inspected.

Protocol: `historical_universe_feasibility_protocol.md`, committed on main as
`752b8c1` before implementation/execution.

### Observed archive roots

| Monthly root | All directories | USDT-format directories |
|---|---:|---:|
| USD-M trade klines | 1,080 | 918 |
| USD-M mark klines | 1,068 | 919 |
| USD-M funding | 1,011 | 919 |
| Spot klines | 3,767 | 774 |

The trade/mark/funding USDT-format directory intersection contains 918 identifiers.
These counts are discovery-time inventories, NOT counts of eligible crypto
perpetuals in 2021-2026. They include identifiers requiring contract/product
classification and do not prove overlapping data. The current exchangeInfo
snapshot has 659 USDT perpetual identifiers; 265 trade-archive USDT identifiers
are absent from that snapshot. Absence alone does not prove delisting.

### Frozen pilot, 2021-01 through 2026-10

| Identifier | Trade months | Mark months | Funding months | Required common months |
|---|---:|---:|---:|---:|
| BTCUSDT | 70 | 70 | 70 | 70 |
| ETHUSDT | 70 | 70 | 70 | 70 |
| LUNAUSDT | 17 | 19 | 17 | 17 |
| LUNCUSDT | 0 | 0 | 0 | 0 |
| FTTUSDT | 55 | 55 | 39 | 39 |
| WAVESUSDT | 70 | 70 | 54 | 54 |

All matching pilot monthly ZIPs have adjacent CHECKSUM objects. This establishes
checksum-file availability only, not content or checksum correctness. LUNCUSDT
has spot files but no exact-name USD-M pilot files; do not silently substitute
another contract, including a scaled identifier. LUNAUSDT spot history and futures
endpoints differ; token migrations/identifier reuse must not be stitched blindly.

### Critical metadata inconsistency

The official [WAVES announcement](https://www.binance.com/en/support/announcement/detail/f65faeeefe07417a8b6dd2900ba8da7e)
states futures automatic settlement/delisting in June 2024, but monthly trade and
mark filenames extend to October 2026 and funding filenames to June 2025. FTT
trade/mark also extend beyond the funding archive endpoint. File presence is not
evidence of trading, valid funding events, or continuous eligibility. A bounded
row pilot must distinguish usable observations from potential post-lifecycle
artifacts; the metadata pilot has not examined ZIP contents.

### Acquisition footprint and reproducibility

- Successful public metadata requests: 35; no request errors.
- Response bytes: 2,602,188 (approximately 2.48 MiB).
- Market ZIP downloads: zero.
- Ignored evidence: `data/interim/universe_feasibility/20261117_metadata_pilot/`.
- `manifest.json`: request URLs, retrieval times, response byte sizes and SHA-256.
- `summary.json`: complete discovery identifiers, pilot file metadata and decisions.
- Six-pilot total compressed ZIP size: approximately 25.82 MiB, not an all-universe
  estimate and not authorization to download that dataset.
- Five synthetic XML, pagination and coverage checks pass; Ruff passes.

Reproduce into a NEW output directory (existing evidence is not overwritten):

```bash
python3 scripts/check_universe_feasibility.py \
  --output-dir data/interim/universe_feasibility/<NEW_RUN_ID>
```

A metadata run took approximately 10-20 seconds here. Network latency can vary.
The command prints a compact decision; consult `summary.json` for failed gates.

## Next boundary

The infrastructure can retrieve historical metadata. A complete point-in-time
investable universe has NOT been established. Before bulk acquisition: inspect
a separately registered bounded row pilot, reconcile exact contract lifecycle
and symbol identity, enumerate per-symbol coverage, then quantify transfer/storage.
Hourly mark data still cannot reconstruct intrabar liquidation or order-book depth.

## Separately registered lifecycle row pilot

Protocol: `lifecycle_row_pilot_protocol.md`, committed on main as `96ed53b` after
the metadata conclusion and before row inspection. The original failed gate is
unchanged. This follow-up diagnoses the failure; it does not relabel it a pass.

Decision: bounded transport/parsing is feasible and the late-file-artifact test
passes. Full historical tradability and full-download readiness remain unproven.

All 12 fixed samples matched official SHA-256 checksums and archive sizes, contained
the expected single CSV, and passed timestamp uniqueness/order and finite-value
parsing checks. Positive-volume trade rows are observations, not full proof of
executability. Mark-volume fields are not used as trade-activity evidence.

| Sample | Rows | Positive-volume trade rows | Finding |
|---|---:|---:|---|
| BTC trade 2024-05 | 744 | 744 | Control parses normally |
| BTC funding 2024-05 | 93 | n/a | Funding control parses normally |
| WAVES trade 2024-05 | 744 | 744 | Pre-event control |
| WAVES trade 2024-06 | 720 | 249 | Last positive-volume bar starts 2024-06-11 08:00 UTC |
| WAVES trade 2026-10 | 744 | 0 | All OHLC values one constant price |
| WAVES mark 2026-10 | 744 | n/a | All OHLC values one constant price |
| WAVES funding 2025-06 | 56 | n/a | All rates nonzero, despite earlier lifecycle event |
| FTT trade 2026-10 | 744 | 0 | All OHLC values one constant price |
| FTT funding 2025-06 | 56 | n/a | Nonzero rates do not prove tradability |
| LUNA trade 2022-05 | 295 | 280 | Partial terminal-month observations |
| LUNA mark 2022-06 | 720 | n/a | All OHLC values one constant price |
| LUNA funding 2022-05 | 37 | n/a | Funding endpoint differs from mark endpoint |

No historical strategy returns were computed. In particular, late funding rows
must not be booked as realizable cash flow merely because they are nonzero.
Their exact production mechanism is unresolved. Constant, zero-volume trade rows
are a supported late-file artifact here, not a universal rule for detecting
delistings; legitimate illiquid bars may also have zero volume.

- Requests: 24; errors: zero.
- ZIP bytes: 123,510 (approximately 121 KiB); all responses: 124,627 bytes.
- Evidence: ignored `data/interim/universe_feasibility/20261117_lifecycle_rows/`.
- Reusable script: `scripts/check_lifecycle_rows.py`.
- Nine focused synthetic checks, Ruff and formatting checks pass.

Reproduce (approximately 5 seconds here, network-dependent):

```bash
python3 scripts/check_lifecycle_rows.py \
  --metadata-summary data/interim/universe_feasibility/20261117_metadata_pilot/summary.json \
  --output-dir data/interim/universe_feasibility/<NEW_ROW_RUN_ID>
```

Success criteria: `summary.json` has `transport_parsing_feasible: true`,
`late_file_artifact_supported: true`, 12 samples and an empty errors list.

## Recommended acquisition sequence

1. Metadata census of all discovered USDT identifiers for trade, mark and funding
   in the fixed window. Filter dated contracts/non-crypto products using recorded
   evidence; retain unresolved identities rather than silently accepting them.
   Report month-level overlap, gaps, checksums and exact compressed-byte totals.
   Do not select only symbols that survived to the end of the window.
2. Build a sourced contract-lifecycle ledger, with instrument identity, multiplier,
   event/effective time, announcement/publication or observation time, source and
   confidence. Archived endpoints are bounds, not listing/delisting facts. Preserve
   migrations and scaled contracts as separate identities until explicitly mapped.
3. Acquire a bounded batch including active and terminal-event contracts. Reuse
   existing files only after content/provenance verification. Separate real trade
   activity, mark observations, and funding eligibility. Preserve inactive rows in
   raw evidence, but do not extend tradability or earn simulated funding from them.
4. Decide and register portfolio eligibility/accounting rules before strategy
   performance inspection. Historical eligibility must use only then-known facts;
   never remove an asset's entire history because its future delisting is known.
   Announcement availability, forced exits, settlement prices and missing data need
   explicit treatment. Lifecycle facts may also serve as an ex-post audit reference,
   which is distinct from information available to a trading decision.
5. Scale acquisition only after the batch quality report and download/storage
   budget are accepted. A full-universe size/runtime estimate is not yet measured.

Spot is optional for a perpetual-only factor study unless its chosen signal,
liquidity rule or comparator requires it. Requiring same-name spot by default
would introduce unnecessary exclusions and does not resolve token identity.

Overall: suitable infrastructure and recoverable historical samples support
continuing data preparation. They do not yet support a survivorship-free factor
backtest, performance claim, or direct bulk-to-backtest pipeline.
