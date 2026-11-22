# Completed2020 observation release and daily long panel

2026-11-19. Preregistered on main at `37f3cf3`:
[early_research_protocol.md](early_research_protocol.md).
Tools:`scripts/build_early_research.py`,`scripts/early_research_rules.py`.
Scope2020 only;partial2019 API samples are not inserted as complete history.
No new downloads,factors,forward labels,model fits,PnL or OOS performance.

## New release

Shared data root:`canonical/binance_um_early_research/v20261119_001/`.
Full build completed locally in85.578s,zero errors. Old canonical,raw,review and
daily releases,registered calendar and approved split remain unchanged.

| Output | Count |
| --- | ---: |
| Archived contract identifiers with early files | 81 |
| Verified original source partitions | 1526 |
| Normalized observation partitions | 1527 |
| Trade hourly rows | 344043 |
| Mark hourly rows | 346321 |
| Funding observation rows | 43058 |
| Daily panel rows | 29646 |

The extra partition contains31 QTUM February API observations;the March sentinel
is not duplicated.81 means archive identifiers,including a composite index,not
81 eligible crypto coins. `universe_coverage.json` also retains the frozen924
identifier inventory and absent-file annotations without inventing daily prices
for the843 identifiers with no early files.

## Structure and usage

- `observations/{trade,mark,funding}/{symbol}/{YYYY-MM}.parquet`:compatible
  observation fields,raw decimal strings,source SHA/URL/retrieval metadata and
  additional row-level audit flags. Funding intervals and event mark prices are
  typed nullable fields;all publication timestamps remainunknown.
- `daily/{symbol}.parquet`:366 UTC data days per observed identifier. Each row
  represents one date/instrument,with observed closes,hour counts,volume/taker
  sums,latest strictly earlier funding event and age,history diagnostics and
  known/proposed boundary flags. Empty days have null prices/volume sums,not
  artificial zeros;hour-count zero explicitly means no source hours. Partial
  day sums contain only observed hours and must be read with completeness flags.
- `index/{symbol}.json`:output hashes/counts and original source bindings.
- `source_verification/`:fresh raw checksum/provenance/CSV quality verification.
- `lifecycle/`:partial confirmed events and ex-post review policy,not a complete
  or certified causal universe. `manifest.json` and `run_config.json`:scope,
  counts,hashes and unresolved gates.

Daily endpoints20/60/120 and121 contiguous valid closing observations are
separate diagnostics,no momentum return values. A first partial trading day can
supply a real close but fails24h completeness. Zero-activity days break closing
history. Next UTC midnight is a reference/lower-bound convention,not a selected
execution clock or proven publication time. Latest funding is an observed event,
not a forecast or automatic forward-filled charge;age/freshness remain explicit.

The existing `momentum_data.reader.ResearchData` observation interface was
checked against the real pilot:24 BTC hours,31 QTUM observations,and blocking a
read crossing the known LEND settlement. It remains an observation reader,not a
trading eligibility or funding-accounting engine. This schema2 release is not
silently plugged into the old hardcoded2021 builders.

## Restrictions preserved

- QTUM:all31 supplement intervals and event mark prices remainnull.2 observations
  before the proposed launch are quarantined;the HTTP202 announcement source
  gate remains unresolved. No historical8h rule inferred from spacing/March.
- DEFI:composite index flag;single-token price-history candidate false. Known
  prelaunch observations retained/quarantined,not joined to a same-ticker token.
- LEND:postsettlement rows retained/quarantined;earlier history retained. Separate
  AAVE launch starts a separate instrument history;no100:1 price splicing.
- Full-release quarantine flags:trade753,mark1299,funding6 observations. These
  rows remain present. Flags are ex-post reconstruction restrictions,not proof
  that all other rows are tradable or all marked funding was unpaid.
- Other lifecycle origins remain explicitly unverified. Historical Size is not
  integrated;publication times,exact settlement marks,cashflows,final eligible
  universe and strict trading readiness all remainunproven/false.

## Validation and repeatability

157 tests pass (9 new);new files Ruff lint/format pass. Synthetic checks cover
unknown fields,confirmed versus proposed boundaries,history gaps,zero activity,
strict funding cutoff,index exclusion,LEND/AAVE separation,uniform null schemas,
round-trip equality and conflicting output rejection. Native Python3.11/Arrow11
tested;configured project3.13.

Six-instrument pilot(BTC,ETH,QTUM,DEFI,LEND,AAVE):143 original partitions,
144 outputs,2196 daily rows;16.625s. Verified resume6 hits11.109s. Full1527 output
Parquet hashes and metadata row counts plus all81 daily schemas/counts checked
independently;QTUM null fields/quarantine counts explicitly verified.

No user command is needed now. To read status:

```bash
python scripts/build_early_research.py summary
```

To verify/resume the same immutable full release when needed:

```bash
conda activate funding-strategy
python scripts/build_early_research.py full --workers 4
```

Only one host/writer per output. Resume revalidates raw and output hashes and
fails on changed inputs/code;new definitions need a new release path/version.
Log:`reports/acquisition/early_research_full_20261119.log`.

Next bounded task:earlier historical Size/identity coverage and remaining2019
source feasibility,then a separately registered combined-history build. The old
2021 warm-up flags do not automatically change just because this release exists.
Training-date changes require an explicit protocol amendment before performance.
