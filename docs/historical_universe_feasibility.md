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
