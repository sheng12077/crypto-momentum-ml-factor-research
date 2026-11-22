# Early history and funding backfill

Protocol registered on main at `fc0238c` before implementation:
[history_extension_protocol.md](history_extension_protocol.md).
Tools: `scripts/extend_usdm_history.py`, `scripts/probe_2019_history.py`.
No original census,download or canonical outputs were overwritten. No old frozen
tool dependencies modified;no strategy fit,return,PnL or OOS performance viewed.

## Verified archive inventory

All924 frozen identifiers/2772 cached listing jobs were verified against saved
official response hashes,URLs,prefixes and pagination. Reparsed2021--2026 file
count/bytes exactly match the original census. Zero metadata HTTP requests.
Inventory took97.688s on native Windows/WSL UNC.

Search window2019-01..2020-12 yields **only2020 monthly archives** in this frozen
evidence. A platform's2019 launch is not evidence of2019 monthly files.

| Series | Files | Identifiers | Earliest month |
| --- | ---: | ---: | --- |
| Trade1h | 509 | 81 | 2020-01 |
| Mark1h | 510 | 81 | 2020-01 |
| Funding | 507 | 81 | 2020-01 |

Total1526 files/24,153,565 compressed bytes,zero checksum-object gaps. Every
month's overlap is exported,not inferred from current membership. Examples:
three-series archive counts11 in2020-01,30 in2020-06,80 in2020-12. These are
monthly file-presence counts,not same-day eligible assets or complete121-close
histories. Historical Size and identity eligibility still require extension.

Inventory root:`data/interim/usdm_universe/history_extension_20261118/inventory/`:
`download_plan.json`,`pilot_plan.json`,`coverage.json`,`monthly_counts.json`,
`checksum_gaps.json`,`funding_reconciliation_queue.json`,`summary.json`.
The reconciliation queue covers2019--2026-10 and163 identifiers with funding/bar
archive-month mismatches. These are review leads,not163 proven missing payments.
Check lifecycle boundaries/inactive artifacts before fetching or filling anything.

## Completed samples

- BTC/ETH earliest trade/mark/funding sample:6 January2020 files,124,307 bytes.
  Official SHA,size,CSV checks pass,zero errors/missing hours/nonpositive prices.
  Verified resume:6 cache hits,zero downloads. Available six-file count matches
  the bounded pilot,not the failed exact12 test from the original project stage.
- All134 regression tests pass,13 new;three changed Python files Ruff lint and
  format checks pass. Native Python3.11;configured project3.13.
- Full1526-file raw extension subsequently downloaded by user:1520 downloads,
  6 cache hits,zero errors,24,153,565 bytes. Independent offline audit complete;
  see [EARLY_HISTORY_AUDIT.md](EARLY_HISTORY_AUDIT.md). No rerun needed. The
  WSL commands below remain available for reproducible acquisition/resume.

## Bounded2019 public API evidence

Three fixed BTCUSDT requests,2019-09-14,each limit2;all HTTP200. No retries or
alternate-host probes. Results:

| Input | Observed sample |
| --- | --- |
| Trade00:00--01:00UTC | One hourly bar |
| Mark,same hour | Empty list |
| Funding,that day | Two observed events;associated markPrice absent/empty |

Raw responses,hashes and metadata preserved in
`data/interim/usdm_universe/history_extension_20261118/api_2019_probe/`.
`success=true` means all fixed requests were parsed,not that all series exist.
`full_2019_coverage_proven=false`. No claim about every other2019 mark interval
or all contracts follows from this single sample. No rates or prices synthesized.
An empty funding markPrice does not become the neighboring hourly close.

Official funding-history docs describe event time,rate and an associated
[markPrice field](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History);
field presence in a schema does not guarantee old observations populate it.

## Full archive command in WSL

From the repository directory:

```bash
conda activate funding-strategy
python scripts/extend_usdm_history.py download --max-gib 0.03 --workers 2
python scripts/extend_usdm_history.py summary
```

0.03GiB is an explicit compressed ZIP budget,not total disk usage. Requests/evidence
retain copies. At least256MiB plus cache/evidence overhead is checked by the
existing downloader. This command uses the completed immutable inventory;do not
rerun inventory or change old frozen acquisition tools merely to launch it.
No credentials or paid data required. Do not run concurrent Windows/WSL writers.
On interruption/transient failure,rerun the same command;verified cache reused.
Integrity failures must be investigated,not deleted to force success.

Log:`reports/acquisition/history_extension_download_20261118.log`.
Download report:`data/interim/usdm_universe/history_extension_20261118/download/summary.json`.
Shared raw cache:`../../data/raw/binance_um_universe/`,existing names/provenance
validated;new extension acquisition reports remain in their own directory.

Expected full RAW result:success=true,errors=[],planned_files=verified_files=1526,
planned_compressed_bytes=verified_bytes=24153565. At least the6 pilot files should
be verified cache hits unless evidence is unavailable on that host. Additional
reusable caches may change downloaded/cache counts. Readiness remainsfalse.

After acquisition:independent normalization/row-gap checks,funding interval/time/
sign/settlement-price reconciliation,then earlier Size/identity coverage. Define
a bounded2019 API backfill plan from actual endpoint coverage;do not claim the
2020 archives complete2019. Exact settled mark pricing,terminal accounting and
historical publication/vintage remain unresolved. Index/premium data are optional
diagnostics,not an unrestricted additional download. Current fundingInfo rules
must not be applied retroactively. Original training/calendar/OOS protocol stays
unchanged until an explicit versioned amendment before performance experiments.
