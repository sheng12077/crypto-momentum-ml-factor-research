# First remaining early identity batch

Registered on main at `1cb44f7`; implementation branch:
`research/early-identity-batch1`. Scope:2020 metadata identity corroboration only.
No canonical joins,feature values,labels,models,PnL or OOS performance.

## Completed result

- Eight identifiers reviewed;five corroborated identity-only rules:ETH1027,
  EOS1765,LTC2,XRP52,LINK1975. These cover170 price-history diagnostic asset-weeks
  within their stated scopes. This does not certify execution or strategy eligibility.
- BTC1 and BCH1831 have consistent historical/current identities and venue name
  evidence,but their designated futures-overview source returned HTTP202. Both
  remain pending;this is a capture gap,not evidence they were untradeable.
- ETC1321 has matching historical/current labels and a verified futures launch.
  The official upgrade article's title contains the full name,but its body only
  says ETC. The preregistered body-only name gate remainsfalse;no title fallback.
- LINK's Ethereum address matches both current CMC and official Chainlink token
  documentation. Its old Binance listing body renders `ChainLink ( LINK )` due
  to inline HTML markup. A whitespace-only parser correction restores the same
  configured name association;it does not accept a different name or article.
- All81 identifiers remain in the review queue. Of40 with2020 price-history
  candidate weeks,IOTA plus these five now have corroborated identities;34 still
  need work(three reviewed/pending and31 outside this batch). Earlier LEND/AAVE
  identity rules remain separate;neither has a qualified120-day2020 price window.

Capture:21 new HTTP requests,20 successful raw bodies,6,980,389 stored bytes;
one terminal HTTP202 failure. `source_capture_complete=false` is preserved.
`review_001` retains the initial LINK spacing mismatch;`review_002` binds the
corrected parser and outputs. Frozen-source replay makeszero new HTTP requests.
No acceptance gate was waived.185 tests pass(seven new),and changed-file Ruff
lint/format checks pass. Old release versions and OOS permissions are unchanged.

## Selection and acceptance

Recompute the full81-identifier inventory from hash-verified daily panels and54
historical CMC snapshots. The result must equal the prior per-asset queue. Sort
by descending price-history diagnostic weeks,then symbol;select the first eight
not covered by the earlier IOTA/LEND/AAVE review. Retain every other identifier.
This uses data coverage to prioritize work,not returns or survival to select a
trading universe.40 identifiers have qualified2020 price-history weeks;IOTA has
a separately corroborated alias. The first remaining batch covers273 candidate
asset-weeks before scope/identity gates.

| Instrument | Expected historical CMC ID | Candidate asset-weeks before scope gates |
| --- | ---: | ---: |
| BCHUSDT | 1831 | 35 |
| BTCUSDT | 1 | 35 |
| ETHUSDT | 1027 | 35 |
| EOSUSDT | 1765 | 34 |
| LTCUSDT | 2 | 34 |
| XRPUSDT | 52 | 34 |
| ETCUSDT | 1321 | 33 |
| LINKUSDT | 1975 | 33 |

A rule needs consistent dated historical ID/name/symbol,an exact current provider
ID/name/symbol match,an independent Binance name association,and a futures
instrument source. LINK also needs an exact Ethereum address/platform match to
official Chainlink documentation. Current data only corroborates identity;it
does not supply historical membership,market-cap values or availability times.
The resulting association is a documented inference,not on-chain proof of all
contract history. Missing or conflicting evidence leaves a case pending.

## Episode limits

BCH scope stops at2020-11-15 12:00UTC,exclusive,before the fork described in the
[official fork notice](https://www.binance.com/en/support/announcement/detail/ade106fd65974a9982fc5a32e063d0b0).
This batch cannot approve the later interval or substitute BCHA. EOS later
migration/rebranding cannot supply a new identity to2020 rows. Current redirect
or label mismatch is a reason for further historical review,not permanent removal.

EOS,LTC,ETC and LINK scope starts require exact launch clauses in the designated
official notices. BTC,ETH and BCH lower bounds are the review window,not exact
launch dates. XRP's notice says already launched;its configured conservative
lower bound is the end of the stated announcement day,not a precise launch time.
The latter has no effect on candidate weeks beginning after the120-day warm-up.

All rules retain USD market-cap scale1,no price/history splice,unknown full
specifications,funding cashflows and historical publication/vintage,and false
strict strategy eligibility. Supported candidate asset-weeks in scope are data
diagnostics,not PnL samples or certified tradable observations.

## Artifacts

- Protocol:`docs/early_identity_batch1_protocol.md`.
- Fixed source/assertion plan:`config/early_identity_batch1_20261119.json`.
- Tool:`scripts/check_early_identity_batch.py`.
- Ignored root:`data/interim/early_identity_batch1_20261119/`.
- Log:`reports/acquisition/early_identity_batch1_20261119.log`.

The fixed21-source plan uses public CMC,official Binance CMS/blog and Chainlink
documentation,with a32MiB total/2MiB-per-response limit. Terminal failures remain
frozen;authorization/rate denials stop capture. Successful raw bodies and failed
attempts are hash-checked. Reviews separately bind configuration,tool/dependency
hashes,raw sources,historical snapshots and daily-panel hashes. No paid account,
alternate-host denial bypass or original data edits are involved.

`review_002/` contains `mapping_decisions.json`,`provider_identities.json`,
`evidence_checks.json`,`asset_review_queue.json`,`summary.json` and bound run
configuration. The source/error bodies remain under `raw/`;capture summary
contains transport failures separately from semantic evidence checks.

Next coverage priorities outside this batch:TRX,XLM,ADA,ATOM,DASH,XMR,XTZ,ZEC.
New evidence for BTC/BCH/ETC needs a separately registered follow-up,not automatic
retries or changed gates. Only a later versioned hypothetical-lag Size join can
measure combined feature availability;no market-cap purchase is justified here.
