# Development mark boundary recovery

Registered2026-11-21in experiments/004_development_mark_boundary_recovery.md.
This source-recovery segment does not compute labels/PnL, fit models, inspect
OOS performance, approve identities or alter existing canonical observations.

## Inventory

scripts/recover_development_marks.py screens924verified daily files for2021–2022,
then verifies affected hourly trade/mark partitions against their daily source
index. Targets require a positive same-hour trade volume and no canonical mark.
Zero-activity placeholders are not target evidence. Every target hour/day and
same-day canonical mark overlap is bound into plan.json.

Found2901missing hours across86identifiers and121source-days:

| Date | Source-days |
| --- | --- |
| 2021-07-01 | 73 |
| 2022-07-31 | 42 |
| 2022-04-01through04-04 | 4 |
| 2022-08-01through08-02 | 2 |

Gap classes:1893leadinghours and1008trailinghours;no interior targets in this plan.
These targets were outside the old interior-gap recovery scope. This inventory
does not assert that every historical data-quality issue has now been found.

## Source validation

Use official data.binance.vision daily markPriceKlines1hZIP plus CHECKSUM.
The unchanged recover_mark_daily.py source fetcher verifies cached/new SHA256,
ZIP structure, symbol/day/member, size bounds and valid hourly OHLC via existing
parsers. All overlapping same-day canonical marks must agree exactly as decimals.
A fully missing day has no overlap; its evidence is the official archive and
checksum, not a falsely claimed cross-source match. Partial archives contribute
only observed targets, keeping all other keys missing. HTTP403/418/429stop;
cached404failures are not automatically retried.

Limits:500source-days,1000HTTPrequests,1secondminimum spacing,64MiBcompressed
total,2MiBperZIP,10MiBdecompressed. Public requests need no API credentials.
Per-source raw ZIP/checksum/provenance/results are persisted in a shared cache.
The cache uses an exclusive writer lock across pilot/full runs. Do not run
Windows and WSL writers concurrently: their underlying lock types differ.

## Run/resume

This release was created and byte-replayed with WindowsPython3.11.5/PyArrow11.0.0.
From the project directory in PowerShell, the verified commands are:

```powershell
py -3.11 scripts/recover_development_marks.py plan
py -3.11 scripts/recover_development_marks.py run
py -3.11 scripts/validate_development_mark_overlay.py
```

WSL equivalent for inventory, new recovery versions and read-only validation:

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
data/interim/runtime/nautilus313/bin/python scripts/recover_development_marks.py plan --pilot
data/interim/runtime/nautilus313/bin/python scripts/recover_development_marks.py run --pilot
data/interim/runtime/nautilus313/bin/python scripts/recover_development_marks.py plan
data/interim/runtime/nautilus313/bin/python scripts/recover_development_marks.py run
data/interim/runtime/nautilus313/bin/python scripts/validate_development_mark_overlay.py
```

The inventory has already been run; repeating it verifies its bound plan rather
than replacing changed sources. The run command revalidates successful cached
ZIP/checksum bytes and exports the same overlay when unchanged. Interrupted
transport work is resumable. Do not use --retry-terminal unless intentionally
rechecking an unavailable source; it does not bypass rate-block stopping.
Physical Parquet replay also requires the same writer version. A different
PyArrow version can encode identical rows into different bytes and will be
rejected rather than overwriting this release. Use the read-only validator to
check existing exports from a different environment.

Local audit/cache:
data/interim/development_mark_recovery/v20261121_001/{pilot,full,cache}/.
Full summary:full/summary.json;inputs:full/plan.json;requestresults:
full/source_outcomes.json;codebindings:full/recovery_contract.json.
Log:reports/acquisition/development_mark_recovery_20261121.log.
Cached reruns should need noHTTPrequests for successful sources.

## Versioned output

Shared data root:data/canonical/binance_um_development_mark_recovery/.
Pilot:v20261121_001_pilot/;full:v20261121_001/.
Each contains mark_gap_overlay.parquet,manifest.json,quality_mask.json and
recovery_contract.json. The overlay preserves exact decimal strings and Float64
OHLC, UTCms/timestamps, official source URL/hash/retrieval/raw-payload path.
Every row remains historical_strategy_eligible=false and publication_time_proven=false.

Export validates unique exact keys, recovered/missing partition, correct UTC
open/close times, finite values and numeric/string equality after Parquet readback.
The independent validator reopens rawZIP/checksum/CSV and compares every exported
price as Decimal, every timestamp, source field and recovered/missing target key.
Its report is full/independent_validation.json;no HTTP requests are made.
An existing overlay/version cannot be silently replaced with different data.
Recovery completeness means all2901planned targets, not merely successful HTTP.
Read manifest.recovery_complete and quality_mask.missing_keys before use.

BTC pilot recovered24/24hours for2022-07-31using2requests and920compressed bytes.
This overlay is not yet integrated into the hourly/daily research releases.
After recovery, consume it explicitly in a new versioned build and rerun relevant
coverage checks before claiming the simulation input gap has been resolved.

## Completed full result

- Recovered2901of2901targethours;unresolved0;121source-days/86identifiers.
- Full run240newHTTPrequestsand1cachedpilotday;pilot2requests. All121ZIPs
  total95686compressedbytes;failedsources0;sourceconflicts0.
- Cache replay121cachedsource-days,zeroHTTPrequests,identicalParquetSHA256:
  c19e069f46c47ae01c8b28b1cc5b012bde08bd97a44b7bf6c28458227ef27768.
- Independent rawZIP/checksum/CSVDecimal validator checked every recovered row,
  source field, timestamp and exact recovered/missing partition;passed.
-16newtests and270fullregressiontests passed;1skipbecauseNautilusisnotinstalled
  in the native regression environment. Ruffpassed. No strategy/OOSperformance.

This establishes recovery completeness for this exact2901keyplan. It does not
assert that all historical inputs or every identifier are ready for trading.
