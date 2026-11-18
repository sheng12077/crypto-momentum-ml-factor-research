# Identity follow-up: decisions and corrections

Completed 2026-11-18. Protocol3a68e44, based on exclusion-policy merged504659.
This closes the bounded follow-up on27 priority identifiers. It does not certify
all924 identifiers, a trading universe or point-in-time Size availability.

## Decision registry

The executable policy is config/identity_decisions_20261118.json. Compiler:
scripts/build_identity_decisions.py. All27 cases receive a recorded decision:
24 retained identity candidates and3 temporary whole-identifier Size-join blocks.
Retaining a candidate does not approve its historical join or trading eligibility.

| Temporarily block Size joins | Reason | Re-admission evidence |
| --- | --- | --- |
| KNCUSDT | Legacy/v2 vendor identities are distinguishable, but the futures underlying/index transition remains unestablished after bounded official-source checks. | Futures-specific transition timing and episode-level vendor mapping. |
| DYDXUSDT | ERC20/native vendor IDs differ; mainnet deposits do not establish which underlying/index the futures followed at every time. | Futures-specific index/underlying and supply mapping across the bridge. |
| MDTUSDT | Legacy crypto mapping still unverified; later Medtronic equity is inappropriate for crypto Size. | Resolve legacy crypto separately; an equity strategy needs a different data definition. |

These are Size-join decisions for the current four-component research plan, not
claims that the assets never traded or exclusions from every possible strategy.
All decisions are explicitly ex-post. Freezing them now does not prove a causal,
survivorship-free universe. Original publication/content vintage remains unresolved.

The policy also has8 narrowly scoped blocks (all times UTC; ends exclusive):

| Identifier | Interval | Scope and reason |
| --- | --- | --- |
| BNXUSDT | 2023-02-01 00:00 to2023-02-11 04:00 | Recovered legacy bars have not been integrated into the research release; block consuming them as existing inputs. |
| BNXUSDT | 2025-03-17 09:00 to2026-11-01 00:00 | Captured settlement; no verified later episode. |
| BTCSTUSDT | 2021-03-12 02:00 to2026-11-01 00:00 | Captured settlement; no verified futures relisting. |
| BTTUSDT | 2022-01-14 02:00 to2026-11-01 00:00 | Original contract settled; new1000BTTC is separate. |
| LUNAUSDT | 2022-05-12 15:30 to2026-11-01 00:00 | Original contract settled; LUNA2 is separate. |
| LITUSDT | 2025-12-23 17:30 to2026-11-01 00:00 | Block regular-mode execution until the pre-market transition is verified. |
| PUMPUSDT | 2025-07-10 07:30 to2026-11-01 00:00 | Same pre-market execution limitation. |
| PUMPUSDT | 2025-04-12 14:30 to2025-06-13 09:00 | PumpBTC-specific Size mapping/history unavailable; never substitute Pump.fun. |

The November1 endpoint is the research window limit, not an inferred lifecycle
event. Unknown transitions are not asserted to last through that date; this is a
conservative withholding interval pending evidence. The first five blocks apply
to Size joins and regular execution inputs; the last three have the scopes stated.
BNX/LIT/PUMP/MDT new-episode feature resets are recorded: no rolling momentum or
other state may be carried across unrelated projects, redenominations or relaunches.
An empty result from exclusion_reasons() is only absence of this negative gate,
not permission to trade or join. Other lifecycle/availability/cost gates still apply.

## Corrections supported by the follow-up

**SUN:** its USDT perpetual launched2024-08-22 13:05, after the2021 spot migration.
The earlier assumption that a2021 futures switch needed reconstruction is not
applicable to this contract's launch. CMC10529 identifies Sun[New] and includes the
full Tron address matching the captured Binance migration-completion notice.
Reject old ID6990 for this2024 launch; retain10529 as an identity candidate.
[Official launch](https://www.binance.com/en/support/announcement/detail/adac46dd47b142aebfa1c003c17af568),
[vendor page](https://coinmarketcap.com/currencies/sun-token/),
[migration completion](https://www.binance.com/en/support/announcement/detail/bf95a72b803247ea86904ac16e13087d).

**SATS:** CMC's cached rendering explicitly linked the SATS and1000SATS pages as
denominations of one asset. The direct1000SATS page now returns404; its rendered
excerpt, provider/crawl limitation, URL and hash are preserved separately. This
is not a current raw-page capture or proof of original publication availability.
Use historical ID28683 as the primary candidate matching the futures bundle;
ID28194 remains a separate alternate. No automatic cross-ID splice, duplicate
counting or USD market-cap scaling. [Cached-page source URL](https://coinmarketcap.com/currencies/sats/),
[native denomination](https://coinmarketcap.com/currencies/sats-ordinals/).

**Baby Doge:** earlier manual lookup was case sensitive and missed symbol
BabyDoge. CMC10407 is present on61 captured weekly dates; the vendor page confirms
the ID/name and chain contracts. This corrects a review omission, not a download
gap. Those61 dates include dates outside the futures lifetime and are not61
approved tradable observations. The million-token spot label is already recorded;
historical futures specs and publication/vintage still need their own gates.
[Vendor page](https://coinmarketcap.com/currencies/baby-doge-coin/).

Current official vendor identity pages also establish IDs for five absent-history
candidates; this fixes ID discovery without supplying historical Size:

| Futures identifier | Proposed CMC ID | Current vendor source | Dates in captured305-date first-page history |
| --- | ---: | --- | ---: |
| 1000000BOBUSDT | 34422 | [Build On BNB](https://coinmarketcap.com/currencies/build-on-bnb/) | 0 |
| 1000CATUSDT | 32724 | [Simon's Cat](https://coinmarketcap.com/currencies/simonscat/) | 0 |
| 1000RATSUSDT | 28452 | [rats](https://coinmarketcap.com/currencies/rats-ordinals/) | 0 |
| 1000WHYUSDT | 30867 | [WHY](https://coinmarketcap.com/currencies/why/) | 0 |
| 1000XUSDT | 33108 | [X Empire](https://coinmarketcap.com/currencies/x-empire/) | 0 |

BOB/WHY/X addresses in the current vendor metadata match their captured official
futures notices. Other historical chain/unit mappings remain proposals. First-page
absence is unknown/censored, not zero cap or proof an asset was untradable. These
five need historical data or an explicit missing-Size treatment; no whole-asset
deletion or paid purchase has been made merely because of their absence.

## BNX: what was actually verified

Seven existing raw/normalized partitions were reconciled by official checksums,
raw/index/Parquet hashes and exact timestamps/counts: trade2023-01,2023-02,
2025-03,2025-04,2026-10;mark2025-04,2026-10.

- January2023 trade has744 positive-volume rows. The current February BNXUSDT
  file starts2023-02-22 14:00 and has154 rows, matching the new relaunch period;
  it does not contain the old February contract segment.
- An official BNXUSDTSETTLED S3 listing exists. Its small February ZIP and
  official checksum were captured and verified:511 rows,244 positive-volume
  hours ending2023-02-11 03:00, followed by267 zero-volume rows starting at the
  captured04:00 settlement. Do not import all511 as executable observations.
- Sampled trade April2025 (720 rows) and October2026 (744) each have zero
  positive-volume rows and one distinct price string. The sampled mark files
  are also fixed-price, but mark volume is a placeholder, not trading activity.
- March2025 has a positive-volume bar opening at the09:00 settlement boundary.
  It is not proven tradable after settlement. Similarly a launch-hour bucket
  opening14:00 does not prove trading existed before the14:45 relaunch.
- The small legacy archive is evidence only: it has not been appended to the
  original canonical release, all earlier legacy months are not certified, and
  terminal cashflows still need separate verification.

[Legacy February ZIP](https://data.binance.vision/data/futures/um/monthly/klines/BNXUSDTSETTLED/1h/BNXUSDTSETTLED-1h-2023-02.zip),
[checksum](https://data.binance.vision/data/futures/um/monthly/klines/BNXUSDTSETTLED/1h/BNXUSDTSETTLED-1h-2023-02.zip.CHECKSUM),
[relaunch/routing notice](https://www.binance.com/en/support/announcement/detail/940d0e48493e4627889c3f46371df70b).

## Artifacts and validation

Source list/query log: config/identity_followup_sources_20261118.json.
Inspector: scripts/check_identity_followup.py. Ignored evidence root:
data/interim/identity_followup_20261118/; final audit_003/ and decisions/.
Earlier audit/ and audit_002/ are preliminary and retained, not silently replaced.

17 distinct raw source URLs received terminal checks:15 successful, one404 and
one REST request exhausting three transport/5xx attempts (not retried again in
this round). Raw total7,336,544 bytes. Source capture success remains false;
the bounded evidence audit/decision compilation succeeded with these limitations
explicit. The failed REST route does not invalidate the separately verified ZIP.
No access denial was bypassed, credentials used or further bulk download run.

93 tests pass, including9 new tests for metadata-only parsing, settlement-boundary
and constant-bar counts, exact decision scope, UTC/half-open intervals, rejected-ID
contradictions, no SATS splice/cap scaling, forbidden-access stop and404 cache
integrity. New code Ruff lint/format passes; native Python3.11/Arrow11 used;
configured project runtime remains3.13. Existing unrelated full-tree native
import-order lint is unchanged. No strategy/OOS performance inspected.

The user need not run anything. Optional offline reproduction from the repo:

```bash
conda activate funding-strategy
python scripts/check_identity_followup.py audit
python scripts/build_identity_decisions.py
```

Next segment: bind reviewed episodes and exclusions into a NEW research-input
version, reconcile the recovered legacy hours there, and measure Size availability
inside a separately justified historical universe. Do not restart open-ended
searching for KNC/DYDX here; they remain excluded until specific evidence arrives.
This segment has not executed final universe selection, automatic historical
joins, a paid purchase, Nautilus simulation, paper/live trading or OOS disclosure.
