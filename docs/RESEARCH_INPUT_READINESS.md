# Research-input readiness: bounded source audit

Updated 2026-11-18. Protocol: b863dc2, docs/research_input_readiness_protocol.md.
Status: diagnostic tooling/pilots PASS; complete research inputs NOT READY.
This is step1 data work. No factors, training labels, model fit, own strategy PnL,
backtest, final OOS evaluation, order submission or paper/live setup was performed.
User scope ends at historical trading simulation and OOS review; paper comes later.

## Results and limits

| Area | Verified in this segment | Still required |
| --- | --- | --- |
| Existing observations | Completed release retained; sampled funding partitions checked against frozen index hashes/counts | Historical eligible universe remains false |
| CMC public cap snapshots | 2021-01-03 and2024-01-07,200 rows each; stable numeric vendor IDs/cap/supply fields extracted | Full-calendar coverage, underlying/episode mappings, timestamp/publication/revision assumptions, source terms |
| Coin Metrics public cap | 32/32 BTC/ETH daily observations on two eight-day windows; catalogue exposes135 vendor asset IDs | Coverage of selected assets/history; issued-supply definition differs from circulating cap; vintages/availability |
| Lifecycle | 52 captured official articles;91 events across64 IDs;61/61 priority IDs have partial event evidence | Zero complete lifecycles/specifications verified; causal announcement availability and settlement prices unresolved |
| Funding | 11 local partitions/969 rows audited;12 BTC/ETH API events exactly match archive times/rates | Observed rates are not forecasts; old API-associated mark prices are empty; cashflow accounting remains unverified |

All924 identifiers have a mapping-review entry. Lexical candidates appear for63
against Coin Metrics and187 against the TWO sampled CMC snapshots. These are
review leads, not approved mappings, universe membership or full-history coverage.
No scaled prefixes are stripped, token migrations bridged or unknown caps filled.

## Market-cap sources: do not buy yet

User has CoinGecko/CMC accounts but has not authorized paid data. No key was
requested, read or used; no subscription or purchase was made.

1. CMC public historical webpages provided200 first-page records on each sampled
   date. This is a promising weekly source, not a complete asset database or a
   guarantee of availability for every week. Only cap/identity/supply/update fields
   are extracted; vendor price-change/performance fields are not analyzed.
   Sources: https://coinmarketcap.com/historical/20210103/ and
   https://coinmarketcap.com/historical/20240107/.
2. Coin Metrics Community catalogue and timeseries endpoints work keylessly for
   the bounded sample. Metric CapMrktCurUSD = current issued supply * daily USD
   close. Its definition includes supply some circulating-cap providers exclude;
   do not splice this into CMC circulating cap as if interchangeable. The135
   catalogue entries are vendor IDs, not135 independently verified Binance assets.
   Definition: https://docs.coinmetrics.io/network-data/network-data-overview/market/market-capitalization
   Community: https://docs.coinmetrics.io/packages/coin-metrics-community-data
3. CoinGecko unauthenticated historical probe returned401; keyless CoinPaprika
   old-history probe returned402. These statuses are not determinations of the
   user's account entitlements. No credentials or access restrictions were bypassed.
   CoinGecko Pro docs currently describe two years for Basic and fuller history on
   higher plans; endpoint access must be verified for any eventual purchase:
   https://docs.coingecko.com/reference/coins-id-market-chart-range.
   CMC endpoint/plan coverage likewise needs explicit checking:
   https://coinmarketcap.com/api/resources/cmc-api-historical-data-whats-available-how-far-back-and-how-to-access-it/

A historical timestamp does not prove the value was published then or has not
been revised. Both pilots use available_at=null and historical-version=false.
For example, CoinGecko documents that the prior completed UTC day becomes
available after midnight, so a day label cannot be used as an immediate midnight
signal without accounting for publication delay. A fixed lag can address delay
assumptions but cannot undo retrospectively revised supply or missing old coins.
Coin Metrics documents revisions, historical backfills and reference-data changes:
https://docs.coinmetrics.io/service-and-support/faqs.

Next data acquisition should first inventory weekly CMC snapshot dates/coverage
and validate asset IDs against contract episodes. Only then determine whether a
weekly Size observation is adequate, which absent assets are material, or paid daily
history is justified. Do not buy on the assumption that payment guarantees PIT data.
A top200-history study is a restricted population; future/current membership cannot
be substituted for membership known on each historical date.

## Lifecycle supplement: separate from the frozen release

New curated input: config/lifecycle_facts_20261118.json. New audit:
data/interim/usdm_universe/lifecycle_review_20261118/.
Previous config and lifecycle_review_20261117/ remain unchanged. Increases from
21 to52 sources and47 to91 events are evidence additions, not strategy promotion.
All38 previously unsourced priority IDs now have some official event evidence.
The whole924 ledger still has only64 IDs with captured events and zero complete
lifecycles. All events remain ex_post_only; causal_available_at=null.

Important resolved/avoided errors:
- OMG: earlier Dec16/Dec30 plans were postponed. Record final2025-01-31 09:00 UTC
  from https://www.binance.com/en/support/announcement/detail/1e43c128806544018d3cc537a8add3f6.
  Superseded plans remain source evidence, not false realized settlements.
- PUMP: PumpBTC's PUMPUSDT settled2025-06-13 09:00 UTC; PUMPBTCUSDT launched10:00.
  July's PUMPUSDT is Pump.fun. No free continuation/roll across these identities:
  https://www.binance.com/en/support/announcement/detail/38a74ee47cdc43ebbc672e1dc6968358.
- DOTECO: official source identifies a composite basket index, NOT a separate
  token; launched2021-01-20 07:00 UTC, settled2021-02-19 09:00 UTC. Do not assign
  it DOT's token market cap:
  https://www.binance.com/en/support/announcement/detail/9381a09f6dae4899b8c00046a4afc08b and
  https://www.binance.com/en/support/announcement/detail/b2871bc40ea84e639c2d63b048403b69.
- Spot/margin dates do not establish futures closing dates. Some notices name
  token contracts generically; those facts retain quote/episode scope caveats.

Known CVX/SLP/LIT current-announcement versus archive launch-time conflicts and
all original missing-data masks remain unresolved. This supplement does not
change membership or row eligibility in canonical release v20261117_001, whose
embedded lifecycle snapshot is still the OLD version. Future simulation must
explicitly bind a reviewed metadata version; never silently overwrite the release.

## Funding semantics and remaining accounting work

Fixed pilot: BTC/ETH2021-01 and2024-01; WAVES2024-06; LIT2025-01/12;
PUMP2025-04/07; MDT2024-05 and2026-10. All11 partitions hash/count match the
release index. Source intervals include4h and8h. Exact source event timestamps
are preserved; maximum distance from the nearest interval boundary is20ms.
This is a diagnostic, not permission to round or fabricate settlement times.

For BTC/ETH2021-01-01..02, official fundingRate API returns6 events each. All12
keys and decimal rates match the archive, with zero mismatches/missing keys.
Their markPrice fields are empty: do not claim that an associated price field
means we possess a usable historical settlement price. Hourly OHLC cannot
identify an exact within-hour settlement mark price. Rate history is ex-post
realization data, not proof of a historically available rate forecast.

106 pilot rows occur after a captured settlement without a captured subsequent
launch. This is EX-POST review context, not proof each row is invalid (event
coverage is incomplete), nor proof the cashflow was paid. Missing records,
post-closure artifacts and contract identity reuse must not be zero-filled.

Before account simulation, register and validate:
- the funding rate observation's decision-time availability;
- settlement schedule/position snapshot and event ordering at shared timestamps;
- exact settlement notional/mark sources where available;
- any deliberately approximate price convention and stress bounds where exact
  prices are unavailable (label it an assumption, never source-verified cashflow);
- terminal-event accounting and inactive/relisted-contract handling.
Do not assume a universal8-hour interval or treat current exchange settings as
historical specifications. No margin/fee/liquidation model was implemented here.

## Tooling and reproduction

`scripts/check_research_inputs.py` writes provenance-backed diagnostics under
`data/interim/research_input_readiness/20261118/`:
- summary.json/readiness.json;
- market_cap_pilot.json and cmc_snapshot_pilot.json;
- market_cap_mapping_review.json;
- funding_pilot.json and funding_api_reconciliation.json;
- responses/*.raw and source metadata with URL/retrieved_at/size/SHA256.

Small check, no credentials, existing Arrow environment (already run by agent):

```bash
conda activate funding-strategy
python scripts/check_research_inputs.py
```

Defaults require the new lifecycle_review_20261118/ evidence already present in
this shared workspace. To reconstruct that evidence on a separate checkout:

```bash
python scripts/review_usdm_lifecycle.py \
  --facts config/lifecycle_facts_20261118.json \
  --census-dir data/interim/usdm_universe/census_full_20261117 \
  --audit-dir data/interim/usdm_universe/audit_20261117 \
  --output-dir data/interim/usdm_universe/lifecycle_review_20261118
```

Only one writer/host at a time. Reuse verifies cached bytes/hashes; to refresh
source observations deliberately use a NEW --output-dir. Do not edit cached raw
responses. Full-source metadata is saved; CLI prints a compact summary.

Validation:61 unit tests pass (10 new), Ruff passes, parser tests cover future-date
contamination, duplicate IDs/keys, invalid caps, decimal preservation, missing
coverage, timestamp preservation and cache corruption. Final diagnostic resume:
9 cached HTTP responses, zero fetches, no errors. Native Python3.11/Arrow11 used;
configured project environment remains Python3.13. No full-history cap backfill.
`success=true` means this bounded diagnostic completed, not research-input ready.