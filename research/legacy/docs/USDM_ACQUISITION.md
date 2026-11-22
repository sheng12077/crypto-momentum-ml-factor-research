# WSL Raw USD-M Acquisition

## Prepared scope and measured size

Data-only protocol: `docs/universe_acquisition_protocol.md` (`6aa2634`, registered
before implementation). No strategy performance has been computed.

Completed census: 2021-01 through 2026-10; trade/mark 1h and funding.

- 924 archive-discovered USDT identifiers (includes five Unicode identifiers).
- 2,772 listing jobs; zero errors; 2,771 metadata responses, 44,735,832 bytes.
- 66,893 ZIP files with checksum objects; zero checksum-object gaps.
- Compressed total: 1,035,606,342 bytes, approximately 0.9645 GiB.
- 922 identifiers have at least one three-series overlapping month. GAIBUSDT and
  LENDUSDT have no common month in this window; missing histories remain explicit.
- Current metadata annotates 239 identifiers as non-COIN products; 30 identifiers
  have no record in that snapshot. Neither group is silently filtered by today's
  membership. This raw superset includes non-crypto and unresolved identities;
  it is NOT an eligible crypto perpetual universe.
- Identity/lifecycle ledger includes source provenance and the official WAVES
  effective event. Most historical identity/lifecycle fields remain unresolved;
  snapshot status/onboard/delivery fields are not retroactive eligibility facts.

The census is complete and its RAW acquisition plan is usable. Historical
tradability, canonical factor inputs and investment feasibility remain unproven.
This acquisition does not overwrite sibling canonical datasets.

## Copy into a WSL terminal

No Codex CLI, credentials or third-party Python packages are required. Python 3.12+
on WSL/Linux is sufficient. The commands were checked locally with Python 3.12
and the unit suite also passes with Python 3.13.

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
USDM_MAX_GIB=1.1 bash scripts/run_usdm_acquisition.sh download
```

The 1.1 GiB explicit budget is for the selected compressed ZIP total, not total
disk use. Allow at least 6 GiB free disk for source evidence, shared raw cache,
checksums, provenance, JSON row-quality reports and filesystem overhead. Local
free disk at preparation time was approximately 942 GiB.

Default concurrency is four. Runtime is not established for the full download;
66,893 files require up to 133,786 HTTP requests before cache reuse, so allow for
hours rather than assuming a one-GiB single-file transfer. Reused historical
caches reduce requests. Keep the terminal open. No unbounded retry loop runs.

If interrupted or a transient network failure occurs, run the SAME command again.
Successful files are revalidated and reused; failed requests are retried by that
new invocation. A lock prevents concurrent download writers. Do not remove or
overwrite integrity-failing evidence to force success; provide the error summary.

## Logs, data and compact summary

```bash
bash scripts/run_usdm_acquisition.sh summary
```

- Log: `reports/acquisition/download_20261117.log` (appended on resume).
- Download summary: `data/interim/usdm_universe/download_full_20261117/summary.json`.
- Individual source/row-quality reports: same directory, `files/` and `requests/`.
- New shared raw cache: `../../data/raw/binance_um_universe/`.
- Existing `../../data/raw/binance_core/` caches may be read and reused after
  official checksum, size and provenance checks; they are not overwritten.
- Census results: `data/interim/usdm_universe/census_full_20261117/`:
  `summary.json`, `coverage.json`, `identity_ledger.json`, `download_plan.json`.

Raw acquisition succeeds only when the command exits zero and the download
summary has `success: true`, `verified_files: 66893`, `errors: []`, and
`verified_bytes: 1035606342`. Zero-volume constant-price files and missing hours
are reported rather than treated as trading evidence. `historical_eligible_universe_ready`
must remain false until a separate lifecycle/eligibility stage is complete.
The final summary is the compact result to return for the next research step.

For a verified metadata-only resume, with no market ZIP downloads:

```bash
bash scripts/run_usdm_acquisition.sh census
```

The wrapper uses the already saved local root seed and checks response hashes.
It does not silently refresh the research population or change the window.

## Small-scale validation and registered-count discrepancy

Four-symbol census (BTC, ETH, LUNA, WAVES): 12 listing jobs, 667 available monthly
files, zero errors/checksum-object gaps. The proposed BTC/WAVES two-month Cartesian
sample was registered as 12 files. It actually contains only 11 available files:
WAVES funding 2026-10 is absent, consistent with the preceding feasibility evidence.
The original exact-12-file acceptance count is NOT satisfied; this is a registration
counting error, not a reason to invent a funding file or change the archived result.

All 11 available samples (182,292 compressed bytes) passed checksum, size, safe
CSV parsing and structural checks. Six were reused from existing caches and five
were downloaded. Re-running produced 11 verified cache hits and zero downloads.
The tool explicitly reports the absent combination and sets
`requested_selection_complete: false`; `success` refers only to the available
raw plan. This supports the limited engineering conclusion that the available-plan
acquisition/resume path works, not a claim that the exact-count protocol passed.

The full census is a separate measured available-file plan, and its missing series
are retained in coverage. No full market ZIP download was run during preparation.
18 focused tests cover pagination, corruption, unsafe keys, date/price structure,
resume, concurrency, Unicode membership and current/historical classification;
Ruff and shell syntax checks pass.

## Next stage after acquisition

Resolve product identity/lifecycle events; normalize and audit canonical frames;
separate inactive artifacts from eligible observations; define causal eligibility
and terminal-event accounting. Strategy rules, fitting and comparisons require a
separate preregistration. Never infer tradability from filenames or nonzero funding.
