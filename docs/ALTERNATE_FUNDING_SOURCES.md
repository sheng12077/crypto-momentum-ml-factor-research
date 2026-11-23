# Alternative funding-source investigation

Checked 2026-11-23. Scope: investigate the unresolved June24 funding brackets,
not relax gates or run financial simulations. No provider subscription purchased,
account created, credentials requested, or message sent externally.

## Established local result

The user's complete evidence audit is
`reports/tables/funding_breaks/c946056e6180c28e76cb/evidence.json`:
145/145 brackets return matching REST anchors and no interior observation.
This is not proof of zero payable funding. No strategy records were modified.

## Binance website and Postman

- The supplied [Postman request](https://www.postman.com/api-noob/binance-apis/request/eeusvwt/get-funding-rate-history-market-data)
  uses `{{url}}/fapi/v1/fundingRate`, so it is another client of the same API.
- Probed Binance website's separate public POST history endpoint:
  `/bapi/futures/v1/public/future/common/get-funding-rate-history`.
  VVVUSDT page1/9/10/11 at 100 rows/page were preserved with request/hash metadata
  under `data/repairs/funding_website_probes_20261123/`.
- Date parameters in the initial probe did not bound results; pagination was used
  and actual returned timestamps checked. Website page10 contains VVVUSDT's
  June24 00:00:00.005 and 08:00:00.005 UTC records but no 04:00 record.
  Both anchors still state `fundingIntervalHours=4`. Thus this single-contract
  cross-check does not resolve the interruption as an explicitly recorded interval
  change. It is not a 145-contract website audit or independent collection history.

## Third-party candidates

| Source | Verified capability | Limit for this case |
| --- | --- | --- |
| [Amberdata historical funding](https://docs.amberdata.io/http/market/futures-funding-rates) | `rateType=applied` selects confirmed rates; `isActualFundingRate` distinguishes actual/projected; API requires key | No authorized dataset sample obtained; VVVUSDT/date completeness unconfirmed |
| [Tardis Binance futures](https://docs.tardis.dev/historical-data-details/binance-futures) | Archives real-time exchange feeds, including markPrice; public symbol metadata includes VVV | June24 raw data not accessed; ticker fields are not automatic proof of actual settlement |
| [CoinGlass history](https://docs.coinglass.com/reference/fr-ohlc-histroy) | Funding OHLC endpoint is documented | Close is predicted, not final settled; candle interval is not settlement interval; cannot directly fill costs |
| Coin Metrics community API | Public catalog and VVV history probe attempted | Community funding catalog returned empty; requested VVV market unsupported; no conclusion about commercial coverage |

Tardis [public metadata](https://api.tardis.dev/v1/exchanges/binance-futures)
reports raw-channel id `vvvusdt`, normalized dataset id `VVVUSDT`, available since
2025-01-29, and derivative_ticker coverage through 2026-11-22 at check time.
Reported June collection incidents are on June8/12/22, not June24; absence of an
incident report does not certify uninterrupted data. Free samples are first days
of months, which does not cover June24. [Field semantics](https://docs.tardis.dev/tardis-machine/data-types)
must be checked: next funding timestamps/predicted rates are not interchangeable
with settled costs.

No directly downloadable free replacement for the missing record was verified.
No specific official June24 settlement-pause/deferral announcement was found in
the targeted searches. An unrelated [Binance repository issue](https://github.com/binance/binance-public-data/issues/517)
asks about historical completeness in other intervals; it is not a June24 answer.

## Concrete sample request before spending

Prioritize a single affected contract before any large purchase or integration:

> Please confirm coverage for Binance USD-M VVVUSDT over 2026-06-23 through
> 2026-06-25 UTC. Binance REST and website histories jump from June24 00:00 to
> 08:00 UTC while website records state a four-hour funding interval. Can you
> supply an independently captured sample around June24 04:00 UTC, distinguishing
> actual applied funding from predicted rates and showing exchange/receive times?
> Was funding settled, skipped, deferred, or is the record unavailable? Please
> identify collection provenance and any known gap rather than interpolating.

If a provider only resells the same retrospective REST result, it may reproduce
the gap. Obtain the sample and clarify semantics first. Sending this request is
the user's choice; no external outreach was performed by the agent.
