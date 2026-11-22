# Third early identity batch

Registered on main at `6dfbc42`;implementation branch:
`research/early-identity-batch3`. Scope2020 identity metadata only. No canonical
joins,factors,labels,fit,PnL or OOS performance.

## Completed result

All eight corroborated identity-only rules pass:BAT1697,BNB1839,ONT2566,VET3077,
IOST2405,NEO1376,QTUM1684,THETA2416. Their stated scopes contain214 price-history
candidate asset-weeks. All26 sources captured successfully:26 new HTTP requests,
5,741,950 stored raw bytes,errors[]. All semantic proof gates pass separately.

BAT's exact Ethereum address agrees between CMC and the project FAQ. BNB,VET and
THETA pre2020 completion clauses pass. IOST remains support-only with unknown
historical native phase;passing its project identity does not assert completion.
VEN/TFUEL are explicitly rejected as ticker aliases. No market cap was rescaled.

QTUM's captured original CMS now verifies2020-02-20 08:00UTC launch locally.
This supplements the earlier missing launch evidence;the previous failed Spanish
capture and immutable early release flags remainunchanged. The31 recovered
funding events,includingtwo before this launch,are still not proven paid and
their missing event marks/intervals are not filled. A future phase-data release
would require its own version;this review writes no changes to the old release.

Including prior IOTA and the first two batches,22of40 identifiers with2020
price-history candidate weeks now have corroborated identity mappings,covering
659 candidate asset-weeks.18 remain unresolved:three reviewed/pending(BTC/BCH/ETC)
and15 outside these batches. This is not22 simultaneous or fully tradable assets.
All81 inventory entries are retained. Prior LEND/AAVE identity rules remain
separate and havezero qualified120-day2020windows.

Full suite197 passed(seven new tests);changed-file Ruff lint/format pass.
New/prior frozen-source replay makeszero new HTTP requests. No acceptance gate
changed after capture. Size vintage,full specifications,cashflows and strict
historical strategy eligibility remainunproven;OOS remainssealed.

## Registered cases and special gates

| Instrument | Expected CMC ID | Candidate weeks | Additional evidence/limit |
| --- | ---: | ---: | --- |
| BATUSDT | 1697 | 29 | Exact Ethereum address from current CMC and official BAT FAQ |
| BNBUSDT | 1839 | 29 | Binance Coin/BNB aliases;2019 mainnet swap completion |
| ONTUSDT | 2566 | 29 | Ontology name plus original futures launch |
| VETUSDT | 3077 | 29 |2018 VEN-to-VET completion;VEN is not a VET ticker alias |
| IOSTUSDT | 2405 | 28 | Mainnet support statement;completion/native phase not proven |
| NEOUSDT | 1376 | 28 | Later N3 migration not applied backward |
| QTUMUSDT | 1684 | 28 | Launch evidence cannot repair funding cashflow/event-mark gaps |
| THETAUSDT | 2416 | 14 | THETA/Theta Network/Theta Token names;2019 completed swap;exclude TFUEL |

The214 candidate asset-weeks prioritize work;they are not a required pass count
or independent return samples. Prior batches and all unresolved cases stay in
the81-item queue. Same batch1/2 ID/name/symbol,historical collision,official
body-only name and exact futures-launch gates apply. Names cannot override IDs.

BAT's Ethereum address is
`0x0d8775f648430679a709e98d2b0cb6250d2887ef`;the
[official BAT FAQ](https://basicattentiontoken.org/FAQ/) independently identifies
the contract. Current Solana or wrapped-token entries cannot replace that check.
For native assets,unrelated wrapper contracts do not prove their original chains.

The [BNB completion notice](https://www.binance.com/en/support/announcement/detail/360027291331)
and [VET completion notice](https://www.binance.com/en/support/announcement/detail/360008162992)
are dated pre2020. The latter describes1VEN-to100VET distribution;this does not
authorize multiplying USD market cap or joining old VEN prices. The
[Theta completion notice](https://www.binance.com/en/support/announcement/detail/360025803011)
keeps THETA and TFUEL distinct. The2019 IOST notice supports a swap but does
not establish completion;its unknown phase is recorded explicitly.

NEO2024,QTUM2025 and VET2021 name notices are retrospective identity evidence,
not2020 availability,chain state or feature inputs. All scopes end2021-01-01
exclusive. Full specifications,Size publication/vintage and funding cashflows
remain unproven;market-cap scale stays1 and history splicing staysfalse.

## QTUM limitations preserved

The ordinary public CMS representation of the known QTUM launch code is a new
registered capture,not an overwrite/retry of the old Spanish HTML capture.
All prior failed evidence stays intact. Regardless of this new result,the31
recovered funding observations still lack proven event marks/reported intervals;
two precede the proposed launch. No payment,8-hour schedule or missing price is
inferred. See `docs/EARLY_CASES_REVIEW.md` for the original funding audit.

## Artifacts and reproducibility

- Tool:`scripts/check_early_identity_batch3.py`.
- Plan:`config/early_identity_batch3_20261119.json`.
- Protocol:`docs/early_identity_batch3_protocol.md`.
- Ignored root:`data/interim/early_identity_batch3_20261119/`.
- Log:`reports/acquisition/early_identity_batch3_20261119.log`.

Fixed26 sources,32MiB total/2MiB per response. Authorization/rate denial stops
capture;terminal failures are frozen,with no alternate-host denial bypass.
The NEO discovery article that returned429 is not requested by this plan;the
designated2024 article is a different name source. Previous two batch reviews,
54 historical snapshot raw/parsed hashes,81 daily-panel hashes and original queue
are revalidated before new decisions. The cumulative queue preserves batch1/2
statuses alongside batch3. Reviews bind source/config/tool/dependency/prior-review
and panel hashes. Frozen-source replay useszero new HTTP.

`review_001/` contains mapping decisions,provider identities,evidence checks,
cumulative queue,summary and bound run configuration. Previous batch1/2 statuses
are preserved alongside the new batch3 status. The original inventory queue is
independently rederived before these status fields are attached.

Next coverage priorities:ALGO,ZIL,KNC,ZRX,COMP,OMG,DOGE,SXP. Register prospective
token-address/name/migration assertions before another capture,particularly for
KNC and SXP. Existing BTC/BCH/ETC and UNI gaps remainpending. A later separately
registered hypothetical-lag Size join must measure actual combined feature
availability;identity corroboration does not prove historical Size publication.
