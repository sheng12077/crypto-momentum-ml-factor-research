# Full-universe retention screen

Completed 2026-11-18. Registered on main at9226252, based ondde16bb. User clarified
the objective: retain as many genuinely usable assets as possible. This segment
screens the entire924-ID ledger, not only the previous27 special cases. No new
download, factor, label, fit, return, PnL or OOS-performance inspection.

## Completed results

| Diagnostic | Identifiers | Interpretation |
| --- | ---: | --- |
| Complete registered ledger | 924 | Includes indices, equities, renamed/reused and delisted products; not924 crypto coins. |
| At least one acquired file | 923 | GAIB has mark/funding but no trade observations; LEND has no acquired files. |
| Positive-volume trade observed | 922 | Some active trading data exists; not lifetime/identity/execution certification. |
| Active trade month with trade/mark/funding files | 922 | At least one calendar month, not a common simultaneous universe. |
| Proposed Size ID association | 433 | Includes manual overrides/current IDs without historical coverage. |
| Captured Size-history lead after whole-component blocks | 426 | Union across dates, before active-month alignment. |
| Active-month potential Size overlap | 405 | Trade activity and an associated CMC observation occur somewhere in the same month. |
| Possible120-calendar-day observed span | 789 | Elapsed time only, not120 valid closes or episode-reset-safe warmup. |

The last two rows are different cohorts, not a guaranteed common intersection.
405 identifiers are not necessarily405 distinct underlying coins or405 tradable
assets on any date. Intra-month timing, source availability, correct historical
underlying and contract phase still need verification. The source CMC page covers
only its first200 entries per date; none of these numbers certifies full-market
coverage or a point-in-time strategy universe.

The quick426-to-detailed405 difference is lack of active-month overlap for21
initial leads. Their price/funding data is retained. No asset is removed from all
research merely because it lacks Size data in an active month.

## Retention and exclusions

- Withhold GAIBUSDT and LENDUSDT from trade-data consumption for this window:
  no positive-volume trade observations are present. GAIB still has other series;
  LEND is ledger-only. Raw records are preserved.
- 149 identifiers with some constant zero-volume trade files also have genuine
  positive-volume observations elsewhere. Keep their other months; do not delete
  their entire histories. Gap/reuse flags likewise remain interval/review issues.
- KNCUSDT,DYDXUSDT,MDTUSDT remain blocked for Size joining under the prior policy,
  not universally removed from price-only research. Eight scoped restrictions
  remain attached to the affected identifiers, not applied as whole-month deletion.
- 239 current noncoin annotations and30 missing-current-metadata annotations do
  not automatically exclude earlier periods. The405 Size-month cohort retains22
  missing-current-metadata identifiers, protecting review of delisted old assets.
- NUUSDT is the one Size-month lead with a current noncoin annotation. Its earlier
  crypto and/or later product identity needs episode-level review. EWTUSDT and
  METAUSDT were quick literal leads with current noncoin annotations but lack
  active-month Size overlap. No ticker collision is declared resolved by a match.

Every retained entry remains historical_strategy_eligible=false and
automatic_join_approved=false. A component or interval block is a negative gate,
not an allowlist. No final investable pool has been selected.

## Outputs and reproducibility

Tools: scripts/screen_full_universe.py and scripts/export_screen_candidates.py.
Ignored root: data/interim/full_universe_screen_20261118/.

- quick/review_queue.json: all924 identifiers with activity, mapping proposals,
  current-type annotations, scoped restrictions and unresolved identity flags.
- full/checkpoints/ and indexes/: per-identifier monthly activity/count diagnostics,
  acquired-report hashes and checkpoint hashes. All924 are represented, including
  identifiers with no trade reports. Reuse rechecks metadata-report/checkpoint hashes.
- full/yearly_instrument_month_counts.json: instrument-month sums; these are not
  counts of distinct assets or simultaneous holdings.
- exports/candidate_lists.json: named922 active/three-series candidates,405
  Size-month leads,789 elapsed-span candidates and2 no-positive-trade IDs.
- exports/review_queue.json: all924 with detailed month counts and prior flags;
  exports/summary.json: reconciled cohort counts and class-review exceptions.
- summary.json and run_config.json in each stage bind input/tool hashes. Sources,
  canonical release and prior evidence/exclusion decisions remain unchanged.

The scanner checks the15MB frozen download plan, prior full acquisition/audit/
release counts and hashes, lifecycle ledger, curated policy binding and CMC review
hashes. Detailed mode validates the key/symbol/kind/month, compressed size,
positive/zero row-count arithmetic and positive-time consistency in all22,635
trade acquisition reports. It TRUSTS the earlier raw checksum audit and does not
freshly verify22,635 ZIPs, every Parquet or every hourly close. The exporter
rechecks924 checkpoint hashes and reconciles cohort/report counts.

Initial loader attempts incorrectly equated the924-ID ledger with the923-ID
file/bounds populations. This implementation assumption was fixed; failed attempts
are retained in append-only logs. The final full run completed with zero errors.
The missing IDs were not silently discarded or fabricated to make counts match.

The five fixed pilot assets passed248 report checks in1.016s in this native
environment. Resume:5 verified checkpoints in0.421s. Because this was fast, the
agent executed the full job:924 identifiers/22,635 reports,91.391s,zero errors.
No user handoff or full rerun is needed. Optional reconstruction in the repo:

```bash
conda activate funding-strategy
python scripts/screen_full_universe.py quick
python scripts/screen_full_universe.py full --workers 4
python scripts/export_screen_candidates.py
python scripts/screen_full_universe.py summary
```

Runtime varies by filesystem. Logs are automatically appended under
reports/acquisition/full_universe_screen_<action>_20261118.log. Progress every50
identifiers; identical commands resume with source/checkpoint integrity checks.
Use one writer/host only; Windows/WSL locks are not interoperable. Unexpected errors
are logged with nonzero exit status. A changed tool/config needs a new output
version; do not edit cached artifacts to force a pass.

Full success criteria already met: success=true,full_scope=true,identifiers=924,
trade_reports_verified=expected_trade_reports=22635,errors=[]. Eligibility and
automatic joins remain false by design. Candidate counts may evolve only with
explicitly versioned evidence/rules, never chosen from strategy performance.

## Validation and next task

99 unit tests pass, including6 new tests for preserving current noncoin/missing
metadata names, retaining useful months beside stubs, no blind prefix stripping,
component-specific exclusion, report identity/count/time tampering and checkpoint
corruption/metadata changes. New scanner/exporter/test Ruff lint and format pass.
The lightweight exporter was verified against the real completed full-screen
counts/hashes. Native Python3.11 used; configured runtime remains3.13. Existing
unrelated native full-tree import-order lint remains unchanged.

Next: construct row-level, episode-aware research inputs and daily qualification
for retained candidates. Reset rolling state at new underlying/relaunch events;
the789 elapsed-span count does not enforce those resets, gap-free closes or actual
120-day history within each episode. Align Size observations by an explicitly
reviewed availability/lag rule and preserve missingness; apply lifecycle, funding,
liquidity/execution and asset-class rules. Report per-date counts and reasons
before selecting portfolio size or revealing OOS. No paid data decision yet.
