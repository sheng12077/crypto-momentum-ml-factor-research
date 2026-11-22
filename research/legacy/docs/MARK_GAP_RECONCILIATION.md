# Mark Gap Reconciliation

Date: 2026-11-17. Protocol registered on main as `7d4f078` before execution.
No strategy returns, interpolation, bulk repair, RAW edits or canonical writes.

## Conclusion

The four common archive-gap windows are recoverable in the tested controls from
the official markPriceKlines API, with exact boundary OHLC agreement. This is a
bounded source-feasibility result, not evidence that every missing identifier can
be recovered or that returned marks imply tradability.

Existing-cache integrity does NOT pass its all-runs gate: nine canonical backfill
runs verify, while one older duplicate BTC run lacks its referenced Parquet. The
failed gate is retained. Verified evidence from the other runs is still usable
as candidate data; no historical source file was recreated or silently relabeled.

## Existing backfills

- Ten manifests, 210 raw response rows. Every raw response passes source/query,
  byte-size, SHA-256, hourly timestamp/close-time and positive ordered OHLC checks.
- Manifests record the old `data/interim/binance_core_audit/series/...` layout.
  An explicit, narrowly scoped path mapping resolves those references to the
  relocated shared `canonical/binance_core_audit/series/...` store. Recorded
  manifests remain unchanged. Initial strict path-rejection evidence is retained.
- Nine canonical Parquets match their raw response key sets, symbols, OHLC and
  close timestamps: 183 rows total.
- Run `20261114T064149Z` lacks its referenced BTC Parquet. Its 27 request URLs,
  hashes and byte sizes exactly match the fully verified `20261114T064243Z` run.
  It is redundant source evidence, not additional observations. It remains failed
  under the registered derived-file check and contributes no accepted candidates.
- Existing fully verified rows cover 153 exact hours from the audited 33,240
  interior mark symbol-hour gaps. The other 30 verified rows are outside that
  particular gap set; they are not counted as repairs here.

These backfills targeted funding-event hours, explaining why they do not repair
the complete hourly margin path.

## Fixed official API probes

One request per BTCUSDT/ETHUSDT/SOLUSDT control and window, plus one post-lifecycle
WAVESUSDT negative-context probe: 13 network calls total, no retry or extra probes.
Every response includes the full requested window and both boundary observations.
Every boundary matches the original monthly OHLC exactly using decimal comparison.
Daily archive fallback was not needed or executed.

| UTC window | BTC | ETH | SOL |
|---|---:|---:|---:|
| 2021-07-24 through 2021-07-27 | 96 | 96 | 96 |
| 2022-10-02 | 24 | 24 | 24 |
| 2023-02-24 | 24 | 24 | 24 |
| 2026-06-29 | 24 | 24 | 24 |

Counts are returned hours in the control window. ETH's July 2021 window was already
present in the archive and serves as an overlap control; its 96 rows are NOT
counted as recovered gaps. Of the 528 returned interior control-window rows
including WAVES, 432 match actual audited missing keys.

Combining these probes with existing verified sources produces 534 distinct
candidate gap rows, with zero OHLC conflicts. The probe adds 381 unique keys beyond
the 153 existing candidates. 32,706 audited mark symbol-hours remain without a
verified candidate in this bounded study. No candidates have been integrated.

WAVES returns all 24 hours for June 29 2026 even though the separately sourced
futures settlement occurred in June 2024. The probe and summary explicitly identify
those 24 candidate rows as post-known-lifecycle context; they must not restore trading
eligibility. The [official API documentation](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price-Kline-Candlestick-Data)
describes the endpoint; actual availability and exact source agreement were tested
here rather than assumed from the documentation.

## Evidence and reproduction

- Initial API/raw evidence: ignored
  `data/interim/usdm_universe/mark_reconciliation_20261117/`.
- Corrected offline reconciliation:
  `data/interim/usdm_universe/mark_reconciliation_20261117_final/`.
- The intermediate `_verified` run is also retained; no saved run was overwritten.
- `summary.json`, `existing_manifests.json`, `probe_results.json`,
  `probe_manifest.json` and `verified_candidates.json` contain the full evidence.
- Offline passes reuse the same 13 hash-verified response payloads: zero additional
  network requests. `bounded_API_requests` counts evidenced responses; consult
  `new_API_requests` and `reused_API_responses` for the actual call distinction.
- Existing-gate CLI exit status is intentionally nonzero because one legacy
  Parquet is missing; this is separate from the 13 complete probe outcomes.
- 30 focused tests and Ruff checks pass.

For an offline reproduction, choose a NEW output directory:

```bash
../funding_carry/.venv/bin/python scripts/reconcile_mark_gaps.py \
  --data-root ../../data \
  --audit-dir data/interim/usdm_universe/audit_20261117 \
  --census-dir data/interim/usdm_universe/census_full_20261117 \
  --download-dir data/interim/usdm_universe/download_full_20261117 \
  --output-dir data/interim/usdm_universe/mark_reconciliation_<NEW_RUN_ID> \
  --probe-evidence-dir data/interim/usdm_universe/mark_reconciliation_20261117
```

This uses the existing sibling Python environment for read-only Parquet checks;
no new dependencies need installation. Omitting `--probe-evidence-dir` performs
the registered bounded API queries again, so retain the option for offline checks.

## Next bounded task

Prepare a resumable missing-key-only source-recovery plan, preserving per-row
provenance, boundary validation, conflicts and unresolved keys. Treat inactive
contracts separately. After acquisition, integrate an explicit overlay into new
versioned research tables rather than modifying old raw or canonical sources.
The non-common mark gaps and 13 trade gap files remain separate unresolved work.
Historical product identity/eligibility remains false; no fitting or strategy
performance work follows automatically from a successful data-recovery probe.
