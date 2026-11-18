# CMC weekly coverage: acquisition handoff

Updated2026-11-18. Registered on main at d65d49b BEFORE implementation/data probes.
Scope: raw public weekly cap/identity metadata. Full305-date acquisition NOT RUN.
No paid access, credentials, trading, model/factor computation or OOS performance.

## Execute in WSL

From the momentum_strategy repository, reuse the existing environment:

```bash
conda activate funding-strategy
python scripts/collect_cmc_weekly.py download --max-mib 256
python scripts/collect_cmc_weekly.py summary --max-mib 256
```

This collector uses Python standard library only (no new packages). Native
Windows alternate interpreter: `py -3.11` in place of `python`. Only ONE host/run
may write this root at a time; Windows and WSL locks are not interoperable.
The agent has already run plan and the registered four-date pilot plus cache-only
resume, so neither needs to be repeated by the user.

Expected job:305 dates total:304 Sundays within2021-01-01..2026-10-31 and the
2020-12-27 carry-in snapshot. Official index lists all305; no requested calendar
holes. The frozen plan SHA256 is
8dd8dd5bde3736138e1efb29ab3915222266cc5d9cd418700ed99cc3d6e6cb46.

Public source: https://coinmarketcap.com/historical/ (no login or paid API).
The collector fetches the first public historical page per listed date, storing
what is actually returned. It does NOT request additional/paginated assets or
prove complete market coverage. Its parsed outputs exclude price changes and
other performance fields. Vendor historical ranks are not used to select a strategy.

## Runtime, storage and continuation

- One sequential HTTP stream, at least2 seconds between request starts. With
  four snapshot bodies cached, a first full run needs about301 new snapshot
  requests. Pacing alone implies about10 minutes, plus network/parsing/storage.
  Full runtime is not measured; do not treat this as a completion guarantee.
- Pilot average suggests roughly150MiB raw HTML for the full calendar. Explicit
  raw-response budget is256MiB, including the calendar, cached bodies and failed
  attempts. Parsed partitions/reports add storage beyond that raw budget.
- Each response is capped at2MiB. HTTP401/402/403/429 stops acquisition and writes
  access_pause.json; a minimum five-minute cooldown respects longer Retry-After.
  Inspect the reason before retrying, especially403. No access bypass or parallel
  retry storm. Transport/5xx failures get at most3 attempts with saved evidence.
- Resume by running the identical download command. Successful raw and parsed
  partitions are hash-verified and reused. Never delete successful files or edit
  cached responses to make an error disappear. An interrupted temporary raw
  write can be retried; an unmanifested final parsed partition requires inspection.
- Tool/parser/plan/ledger changes are rejected for an existing output version.
  Use a new output root for deliberate revisions, preserving the previous run.
- Progress prints every10 dates. Logs are appended automatically; no shell pipe
  is required and process exit status is preserved.

Log: reports/acquisition/cmc_weekly_download_20261118.log.
Root: data/interim/cmc_weekly_20261118/.

- plan.json + raw/calendar.{raw,json}: frozen source calendar/provenance.
- raw/YYYYMMDD.{raw,json}: shared verified successful page bodies/metadata.
- raw/attempts/: bounded failed-request evidence, never parsed as successful data.
- pilot/ and full/: independent configuration-bound parsed partitions, indexes,
  date_coverage.json, vendor_ID_coverage.json, mapping_review.json, summary.json.

## Success criteria

Require exit zero and full/summary.json:

- success=true, full_scope=true, errors=[];
- planned_dates=verified_dates=305;
- identifiers_reviewed=924;
- point_in_time_ready=false, historical_eligible_universe_ready=false,
  all_asset_coverage_proven=false, approved_historical_mappings=0;
- OOS_performance_inspected=false.

If all pages return200 rows, total would be61,000; actual per-date counts are
reported, not forced to200 or filled. dates_not_200_rows is retained for review.
Raw calendar completion is a narrower gate than all-asset coverage/usable Size.
Return the final compact JSON and any nonempty errors. No full-cache rerun is
necessary merely to repeat a successful long job; the pilot verified resume.

## Completed validation

Registered pilot dates:20201227,20210103,20240107,20261025.
Fresh parsed build:4/4 dates,800 records,387 distinct vendor IDs, zero errors;
2 new HTTP requests,2 verified seed-cache reuses from the previous source audit.
Resume:4 cache hits,0 HTTP, identical parsed/source hashes. Combined cached raw
bytes2,210,747 including the calendar. All pages returned200 rows in the pilot.

All924 instruments have review entries;259 have lexical candidates in these FOUR
snapshots. This is not259 approved histories. Two candidate-ID ambiguities:
BTTUSDT -> CMC3718 (old BitTorrent),16086 (new BitTorrent);
LUNAUSDT -> CMC4172 and20314 (different Terra identities).
The tool does not merge these, adjust units, select return continuity or approve
mappings. Existing known-reuse flags are not an exhaustive list of all reuse.
LIT/PUMP/MDT, scaled contracts, renamed tokens and composite indices also need
contract-episode-specific review, even if only one candidate appears in a sample.

Tests:71 unit tests including10 collector tests pass; collector Ruff passes.
Full-tree native lint flags unchanged test_research_data.py import ordering.
Collector tests
cover calendar/carry-in, foreign-link rejection, forbidden-access stop, retry cap,
raw-byte cap, corruption checks, candidate ambiguity/scaled prefixes, and a
synthetic one-date full-mode run/resume/corruption check. That synthetic test is
not evidence the305 real dates have completed. Existing parser tests cover future
snapshot dates, duplicate keys, decimal preservation and performance-field exclusion.
Validated with native Python3.11; no WSL run was launched by the agent this turn.

## Next review after acquisition

1. Reconcile every date, actual row counts, source failures and vintage/lag
   limitations. Snapshots represent historical labels retrieved TODAY; original
   publication timing/revisions remain unproven. Never use current membership
   or future union coverage to select an earlier trading universe.
2. Review vendor IDs by contract episode, using official underlying identity,
   migrations, scaling and dated mappings. Ticker matches are candidates only.
   An approved ID map alone still does not establish historical tradability.
3. Quantify missing Size observations for the eventual eligible universe. Missing
   from a first page is censored/unknown, not zero cap or proof of no asset.
4. Decide whether weekly Size is sufficient or paid daily/extra-asset history
   solves a concrete deficit. Do not mix CMC circulating cap with Coin Metrics
   issued-supply cap without an explicitly designed, registered definition.
5. Continue selected-contract lifecycle/specification and funding/terminal-price
   work. Only then freeze strategy experiments and start formal trading simulation.

Strategy labels/horizons, holdings, buffer thresholds and final OOS dates remain
unregistered; accepted concepts and constraints are in PROJECT_STATUS.md.