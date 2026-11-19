# Completed2020 historical Size coverage inventory

2026-11-19. Preregistered on main at `709ce35`:
[early_size_inventory_protocol.md](early_size_inventory_protocol.md).
Tool:`scripts/inventory_early_size.py`. Coverage only;no purchase,credentials,
approved joins,factor scores,returns,labels,model fits,PnL or OOS performance.
Early canonical data,calendar and approved training/validation/OOS split unchanged.

## Sources and engineering result

54 public CMC dates:52 Sundays in2020 plus2019-12-22/29 carry-in. All listed in
the hash-verified cached official calendar. First public page only,200 rows per
captured date:10,800 metadata rows/427 vendor IDs. Parse only identity,cap and
supply,not rank,price changes or return fields. This does not prove all-asset
coverage. Every page/parsed hash and date title checked;report totals reconciled.

Source capture used53 new HTTP requests overall:3 in the4-date pilot,50 in full;
calendar and2020-12-27 reused verified existing evidence. Full104.61s,errors[],
raw evidence25,042,079 bytes within64MiB budget. Pilot9.906s;verified resume7.703s,
4 cache hits/zeroHTTP. No access denial or paid data used. All164 tests pass
(7 new);changed-file Ruff lint/format pass. Native Python3.11/Arrow11.

## Coverage findings

Denominator:the81 early archive identifiers and52 Monday decision dates. Existing
daily quality diagnostics determine activity/history,not today's asset list.
For coverage only,the old snapshot-end+7d lag/7d expiry assumption is used. Select
the required globally available snapshot;do not substitute an older cap when a
token is absent. This assumption does not prove historical publication/vintage.

| Finding | Result |
| --- | ---: |
| Identifiers with at least one literal historical symbol lead | 74 |
| Approved historical identity mappings | 0 |
| Price-history diagnostic candidate asset-weeks | 862 |
| Candidate asset-weeks with one literal cap lead | 833 |
| Conditional literal-lead coverage | 96.6357% |
| Missing candidate asset-weeks | 29,all IOTAUSDT |
| Weekly literal cap/price-history leads,min/median/max | 0/23/39 |
| Weeks with at least20 such leads | 29 of52 |

An asset-week is one contract at one weekly decision,not an independent return
sample. Unique ticker matching is a data lead,not certified underlying identity,
an eligible four-factor portfolio or a profitability estimate. Fresh-funding
intersection is separately reported;no taker-input/cashflow certification.

17 weeks have zero price-history candidates because the price corpus begins
in2020 and requires121 valid closes. First nonzero2020-05-04:3 cap/price leads;
first20-lead week2020-06-15:20 of21 price-history candidates.2020-12-28 has39
literal cap leads among40 history candidates. Buying market-cap data does not
remove price warm-up or create more historically available futures contracts.

## Named review priorities

1. **IOTAUSDT:**all54 snapshots contain a name-only IOTA/MIOTA proposal,CMC1720,
   but no literal IOTA ticker. This accounts for all29 missing price-candidate
   asset-weeks. Investigate historical contract/unit identity before approving
   this alias;do not call the data absent or scale USD market cap automatically.
2. **UNIUSDT:**historical UNI is not unique across time. CMC4113 is UNI COIN
   (4 captured dates,2019-12-22..2020-02-23);CMC7083 is Uniswap(15 dates,
   2020-09-20..2020-12-27). This cross-date ID change is flagged for review,not
   used as a future-based mask. Never splice same-ticker unrelated assets.
3. **AAVE/LEND:**AAVE literal lead7278 appears2020-10-11 onward. Earlier name-only
   Aave with tickerLEND is2239. Keep the confirmed futures settlement/new-launch
   boundary and separate instruments;name equality does not authorize splicing.
4. **Five other absent literal stems:**1INCHUSDT,AXSUSDT,BELUSDT,FLMUSDT,SKLUSDT
   have no matching literal row in captured first pages. They each havezero
   qualified121-close weeks in2020,though1/6/6/13/3 weeks of observed activity
   respectively. Absence may reflect page scope,unreported cap or other identity
   issues;do not infer nonexistence or assume a paid provider covers them.
5. **DEFIUSDT:**known composite index,excluded from single-token Size leads.

74 literal-lead names and2 name-only proposal names overlap;do not add them as
disjoint groups. All single/multiple-ID leads remainunapproved. Vendor-ID/name
changes are descriptive review findings,not rules selected from future returns.

## Purchase decision and next bounded task

No purchase is justified yet solely by the observed post-warm-up Size gaps:
all29 are the IOTA name/unit-identity case. First verify IOTA/MIOTA and UNI/AAVE
episode mappings,then build a separately versioned hypothetical-lag Size join.
Only price-history/identity-qualified residual gaps should inform a paid data
request. Require provider samples for specific IDs/dates and ask about revisions/
historical availability;paying for a longer series does not prove point-in-time
content. Strict Size publication/vintage and historical eligibility stayfalse.

## Artifacts and status

Ignored root:`data/interim/early_size_inventory_20261119/`:

- `raw/`:54 snapshot bodies plus verified calendar/provenance.
- `calendar_contract/run_config.json`:54 dates and fixed lag/expiry convention.
- `pilot/`,`full/`:parsed metadata partitions/indexes,hash-bound configuration,
  `weekly_coverage.json`,`asset_review_queue.json`,`summary.json`.

No user command needed. Read status with
`python scripts/inventory_early_size.py summary --max-mib 64`.
Log:`reports/acquisition/early_size_full_20261119.log`. Old collectors and frozen
dependencies untouched;new definitions require a new inventory version. No cap
columns have been silently added to the early canonical panel.

Primary public source examples:
[CMC historical archive](https://coinmarketcap.com/historical/),
[IOTA/MIOTA historical row](https://coinmarketcap.com/historical/20200206/).
