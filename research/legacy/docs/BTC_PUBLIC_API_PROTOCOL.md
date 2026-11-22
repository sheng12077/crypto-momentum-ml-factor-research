# BTC public API cross-check

Registered before implementation/acquisition on2026-11-20. Baseline maineeabe9e;
unifiedv007 supports37of40early history candidates;BTC's venue-futures source
gate remains pending. Scope is BTC only,not a new market-wide data acquisition.

## Fixed inputs and expectation

Use public https://fapi.binance.com only,no credentials,private endpoints,
orders,alternate hosts,or network-access workarounds. Seven registered GETs:
exchangeInfo plus trade1h,markPrice1h,and fundingRate for each fixedUTC window:
2020-01-01 inclusive through2020-01-04 exclusive,2020-06-01 inclusive through
2020-06-02 exclusive. Limits1000,API endTime=end-1. Raw budget16MiB,existing
2MiB response ceiling,pacing and bounded transport retries. Stop further new
requests after a capture failure;freeze failures and access restrictions.

Expect current BTCUSDT contract metadata and sampled historical observations
to agree with existing official archives. No outcome is required to pass.
Bind exact hashes of v007 report/proofs,theBTC archive index and six monthly
Parquet inputs,and the already captured official2019ETH launch announcement.
Keep old releases and identity registry unchanged;write a new audit sidecar.

## Acceptance gates

- Metadata:exactly oneBTCUSDT row,pairBTCUSDT,baseBTC,quoteUSDT,marginUSDT,
  contractTypePERPETUAL;integer onboardDate before or at first2020sample.
  Current status/onboardDate are retrospective metadata,not proof of historical
  daily trading permissions,rule versions,or information availability.
- Klines:strictly ordered unique UTC hour timestamps,exact expected coverage,
  closing timestamps equalopen+1hour-1ms,positive finiteOHLC. Compare exact
  Decimal values forOHLC;for trade additionally volume,quote volume,taker-buy
  volumes,and integer trade count. Do not compare mark-price pseudo-volumes.
- Funding:nonempty unsaturated ordered uniqueBTCUSDT events inside requested
  window. Compare exact event timestamp sets and exact Decimal rates to archive;
  do not round timestamps or treat an empty response as agreement. Missing or
  different funding marks/intervals are reported separately,not fabricated.
- All API samples must agree to assert sampled cross-check success. No numeric
  tolerance or acceptance-threshold change after seeing results. A mismatch is
  an audit finding,not an instruction to overwrite an archive.
- A separate identity-evidence assessment may pass only if all sample gates
  pass,the priorBTC numeric/history/name proof gates remain valid,and the frozen
  official2019ETH notice explicitly references switching BTC/USDT contracts and
  the second perpetual contract. This is combined retrospective corroboration
  for the stated2020scope,not full lifecycle,paid cashflow,or2019coverage proof.
- Current API and archives share Binance provenance;agreement is cross-channel
  consistency,not independent ground truth or proof of no historical revision.

## Validation and stopping point

Test wrong instrument/type,duplicate or missing bars,wrong timestamps/decimals,
empty or saturated funding,and immutable/frozen capture behavior. Run the small
audit locally and verify a zero-HTTP replay and report hashes. Capture failures
are an explicitly incomplete check,not data rejection. Provide one user command
if this host cannot access the public API;do not request API keys to bypass it.
No factors,labels,fit,PnL,OOS,canonical joins,or automatic registry updates.

## Completed audit and interpretation

v20261120_001 acquired all seven public responses. Integration then failed because
the initially selected article parser did not support legacyHTML. No data mismatch
was involved. Old contract/captures retained;v002 uses the existing frozen legacy
parser,with unchanged windows,numeric gates,and source clauses. Seven source
metadata hashes and the old contract hash are recorded in capture_seed.json;
verified bodies were copied into v002 without new requests.
Final227tests passed(including8new API-audit tests);changed-file Ruff lint/format
passes. A same-version replay completed2.579s,zeroHTTP,all three report hashes
identical. Summary verifies report hashes before returning its compact result.

v002 completed4.812s,zeroHTTP:7of7checks passed,192hourly bars compared
(96trade+96mark),12funding events. API/archive timestamps and selected Decimal
fields agree exactly. Combined retrospective identity-evidence assessment passes,
including prior numeric/name/history proofs and the explicit2019contract reference.
This does not establish full-period coverage,real-time data availability,paid
funding,or full historical execution/lifecycle rules. Binance remains the common
provenance of both data channels.

Output data/interim/btc_public_api/v20261120_002/{summary.json,checks.json,
source_outcomes.json,btc_identity_assessment.json};raw responses undercapture/.
Log reports/acquisition/btc_public_api_v20261120_002.log. Reusable command:

```bash
python scripts/check_btc_public_api.py summary --version v20261120_002
```

The acquisition is complete,no user key or download is required. The unifiedv007
registry remains37of40;this sidecar has not silently rewritten it. Next task:
register explicit consumption of this BTC evidence in a new identity/eligibility
release,then audit the weekly usable universe before strategy experiments.
