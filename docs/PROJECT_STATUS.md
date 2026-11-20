# Project status

Updated 2026-11-20. Current documentation segment:docs/vip0-fees-slippage.
Parent maina89fb83(engine/scope implementation037c534);selection-workflow
implementation6ed98bb,merged main454e3bc. Earlier weekly
release implementation86e99a3,merged main84efd6c;registration676dc07.
Inspect Git for final documentation merge. No remote push or history rewrite.
Prior BTC API implementationdfe8d7f,merged main8d68fa0;registration1c3117f.
Prior nine-case implementation93631d6,merged maineeabe9e;registration5440693.
Prior remaining18 implementation8a79757,merged main499adcd;registration4de60fe.
Prior unified engine implementationf96e5aa,merged main3a4d867;registration544965e.
Batch3 implementation9155caa,merged main7ab42dd.
Batch2 implementationd3f89de,merged main5a89e04.
Batch1 implementationdb2695e,merged main3d3df0e.
Prior supplement implementationf2a247a,merged mainae2a518.
Completed identity implementation7e1c3ff,merged main5c44dca.
Weekly contract registered on main atee792fa. Inspect Git for final merge hash.
Daily implementation registered on main at93cf6e1. Target main via no-ff merge; inspect Git for
final merge hash. No push/history rewrite. Scope ends at simulation/OOS;
paper/live explicitly deferred until after OOS review.

## Development-selection workflow discussion

- User recallsVIP0and explicitly requests noBNBdiscount;use as tier assumption,
  not authenticated account state. Reference maker0.0002/taker0.0005,additional
  slippage stress0/2/5/10bpsperfillproposed. New non-executable draft:
  config/execution_cost_policy_draft.json;performance/OOSflagsfalse.
- OfficialFAQcalls numeric examples hypothetical;direct publicfee table did not
  render. OfficialVIPsearch index has same reference values,but effective account
  rates and2021–2022historical schedules remainunverified. Do not claim actual
  account fees or historical fee reconstruction;no private endpoint/key used.
- Costs separate commissions on actual fill notional,adverse-price slippage and
  historicalFunding. Maker/taker follows fill liquidity,not limit-order label.
  Do not double-debit implicit slippage. Freeze explicit execution/stress/fee
  assumptions before performance. PublicVIP0reference can support research;
  authenticated account rates are needed only for account-exact claims.
  No model/PnL/OOS;cost-only config is a draft,not an execution gate itself.

- User explicitly chose first-run momentum/funding/aggressive imbalance,Size
  later. NautilusTrader confirmed as execution/account simulation engine.
  docs/FIRST_DEVELOPMENT_RUN_DRAFT.md records confirmed choices and proposed
  5long/5short,gross100%/net0,feature/model defaults;these numbers are drafts,
  not user-confirmed specifications. SHAP remains required. No fit/PnL/OOS.
- Project currently declaresPython3.13;pyproject has no Nautilus/LightGBM
  dependencies. No installation or runtime claim. Pin/check compatible versions,
  implement adapters/accounting/fill tests,freeze explicit fees/funding/latency.
  HourlyVWAP is a stage0proxy,not a default engine fill. Docs support funding
  boundaries but real source timestamps/mark/cashflow mapping must be tested.

- User proposes selecting on2021–2022then examining2023. Draft recorded in
  docs/DEVELOPMENT_SELECTION_WORKFLOW.md;approved split dates remain unchanged.
  Optional inner2021train/2022validation,then eligible2021–2022refit/2023test;
  keep all trials. Freeze selection objective,search budget,rules and refit policy
  before2023inspection. Favorable2023is supporting evidence,not proof of nooverfit.
- If unchanged,refit2021–2023under frozen rules and evaluate2024. If adjusted
  from2023,mark2023as used development validation;do not call it untouched.
  2025Jan–2026OctfinalOOSstayssealed. Numeric acceptance thresholds and full
  executable trading/model/cost rules pending;this is not full preregistration.
- Four candidate cadence/buffer definitions proposed;fixed benchmarks/risk
  metrics discussed. No tests/performance run for this documentation-only segment;
  no fit,labels,PnL,orOOS. Existing performance/oos flags remainfalse.
- Next:complete executable trading/feature/model/cost rules and bounded ledger,
  audit2021–2022identity/universe/warm-up continuity,then preregister/run initial
  development experiments. Current38of40release remains2020/81early IDs only.

## Current identity release and 2020 weekly coverage

- Protocol docs/EARLY_WEEKLY_UNIVERSE_PROTOCOL.md registered676dc07 before work.
  New config/early_weekly_universe_20261120.json;reusable offline command:
  python scripts/build_early_weekly_universe.py summary --version v20261120_001.
- Latest identity source data/interim/early_weekly_universe/v20261120_001/
  asset_review.json:81records,40corroborated overall,38of40ever-history IDs.
  BTC combined evidence consumed,old exact rule retained as superseded,scope/
  USDscale/no-splice/strict limitations unchanged. Other80records unchanged.
  Oldv00737of40 is preserved predecessor,not the current count. BAND/SXP pending.
- Recomputed all7BTC checks from saved raw responses/6archive Parquets and dated
  2019notice;prior tools/dependencies/report/raw metadata/daily inputs hash-verified.
  234tests(7new)passed,Ruff lint/format pass. Full build6.031s/replay4.672s,
  zeroHTTP,all7output hashes identical. No user rerun needed.
- Scope2020only/same81early IDs;52Monday00UTCdecisions,previousUTCday's panel.
  Outputs4212asset-week CSV rows,52weekly JSON/CSV rows,members/exclusion reasons,
  81identity JSON/CSV rows and BTCconsumption record. All counts reconcile.
- Identity/scope/history coverage(all52weeks):min0/median24/max37;first nonempty
  2020-05-04(3names),35nonempty weeks,29weeks>=20names,9weeks>=30names.
  Jul6=24,Oct5=25,Dec28=37;first37-nameweekDec21. Do not assume38everyweek.
- Raw862candidate asset-weeks->844after identity/scope gates:5BAND+6SXPpending
  weeks,7BCHpost-cutoff weeks. All844also pass observed-funding freshness flag;
  this does not prove paid cashflows or whole-period freshness. Strict trading
  eligibility not established;Sizepublication vintage still unproven.
- All old canonical/identity/API releases unchanged. No Sizejoins,factors,labels,
  fit,PnL,OOS. Not a924-ID or2021–2026coverage audit. Next separately scoped
  task:research-input continuity/Sizeavailability/execution-funding semantics;
  do not extend2020identity scopes to later years or run backtests automatically.
- Log reports/acquisition/early_weekly_universe_v20261120_001.log. Current
  report root data/interim/early_weekly_universe/v20261120_001/.

## Completed BTC public API cross-check (consumed in current release)

- User authorized public API checks,no key. Protocol docs/BTC_PUBLIC_API_PROTOCOL.md
  registered1c3117f before work;config/btc_public_api_20261120.json fixes7GETs:
  exchangeInfo and trade1h/mark1h/funding forJan1-3andJun1,2020UTC. Six archive
  Parquets,index,priorv007proofs and captured2019ETHnotice hash-bound. No OOS.
- Reusable script scripts/check_btc_public_api.py. Exact timestamp/Decimal
  comparisons,strict coverage,instrument/type/schema checks;captures and terminal
  failures frozen. Stops furthernew requests after failure;no alternate hosts.
- v001 acquired all7responses;integration hit legacyHTML notice parser mismatch.
  v002 uses existing legacy parser,unchanged gates;all7hash-verified responses
  copied with recorded seed provenance. No source refetch or gate relaxation.
- v002 passed7of7checks,4.812s/zeroHTTP:96trade+96mark hourlybars,12fundingevents,
  exact agreement. Combined retrospective BTC identity assessment true. Current
  metadata is not a historical rulebook;API/archive agreement is not independent
  ground truth. Information availability,paid cashflows,full lifecycle unproven.
- Final227tests passed(8new),Ruff lint/format pass. Replay2.579s,zeroHTTP,
  all three report hashes identical. Source metadata BTCUSDT/PERPETUAL/BTC/USDT/
  marginUSDT;onboardDate1567965300000,currentstatusTRADING. Do not use current
  status or filter values as historical permissions/rules.
- Output data/interim/btc_public_api/v20261120_002/summary.json,checks.json,
  btc_identity_assessment.json,source_outcomes.json;raw undercapture/. Log
  reports/acquisition/btc_public_api_v20261120_002.log. No user rerun/key needed.
- API audit wrote a sidecar only;it is now consumed in the current38of40
  identity release above. Its oldv00737of40predecessor remains intact. BTC is
  no longer pending identity evidence;BAND/SXP still pending. No factors,labels,
  fit,PnL,canonical joins,orOOS access.

## Nine-case follow-up (preserved v007 registry)

- User fullv006 completed108.382s:81records,33identity-corroborated,31of40
  history candidates supported. Sources51available/8terminal failures,42HTTP.
  All five report hashes verified. Newly passedETC,ALGO,ZIL,KNC,OMG,DOGE,KAVA,
  MKR,DOT. RemainingBTC,BCH,ZRX,COMP,SXP,BAND,RLC,SNX,WAVES. No stricteligibility.
- Protocol docs/EARLY_IDENTITY_NINE_FOLLOWUP.md registered5440693 before work.
  New plan config/early_identity_remaining_004_20261119.json:18additional cases,
  60sources,8newURLs;all nine earlier passing assertion objects unchanged.
  Exact v006 summary/runbinding hashes fixed;raw and terminal states inherited
  without copying/refetching old URLs. Prior passed rules must reproduce exactly.
- ExactCOMP Ethereum-address anchors in official docs accepted via opt-in parser;
  provider Ethereum check remains mandatory. ZRX exactID1896/name0x Protocol;
  Band exactID4679/nameBand plus mandatory issuer rebrand notice. BTC uses
  conservative Jan4scope from official Jan3Research report;BCH original CMS
  launch notice,old fork cutoff retained. RLC official Binance.US name is only
  retrospective identity corroboration,not Binance.com listing evidence.
- Full219tests passed;22unified tests include exact-link negatives,wrong network/
  address rejection,predecessor tampering and prior-pass preservation. No old
  frozen helper changed. Full bounded v007 completed85.141s locally,8newHTTP;
  58available,1frozen prior failure,1newHTTP202failure.39corroborated overall,
  37of40history candidates supported(up from31). All33prior passes unchanged.
  Replay62.562s,zeroHTTP,all five report hashes identical;JSON/CSV81unique IDs.
- New passes BCH,ZRX,COMP,RLC,SNX,WAVES with28/10/9/5/3/3in-scope candidateweeks.
  BCHfork cutoff retained. RemainingBTC(ResearchHTTP202),BAND(missing original
  futures source),SXP(current provider lacks legacy Ethereum address;explorer
  lacksSwipe/SXPlabel). UNIalso registered-pending but no2020pricehistorywindow.
  37other IDs need assertions;1DEFIindex retained. No asset silently dropped.
- Outputs data/interim/early_identity_all/v20261119_007/full/;
  log reports/acquisition/early_identity_all_v20261119_007.log.
  No factors,labels,fit,PnL,canonical joins,orOOS. Unavailable evidence stays pending.
- No user download needed;current command is summary --version v20261119_007.
  This bounded work segment ends here. Next separate task:remaining3primary
  evidence or discuss a versioned limited research scope;do not silently dropBTC.

## Remaining18 source plan and full-run handoff (completed v006)

- Scope remains81early contracts. No new eight-case runner. New default plan:
  config/early_identity_remaining_003_20261119.json,18cases/59public sources.
 15new qualified cases plus hashed replacements for BTC/BCH/ETC;old rules retained.
- scripts/run_early_identity.py now prunes pilot cases AND HTTP dependencies;
  mandatory separate migration gate for provider-symbol aliases,exact numericID;
  rejects duplicate cases/invalid assertions/source-budget excess. Frozen helpers
  unchanged;old reviewed rules still reproduced. KNC legacy1982 is never9444.
- ALGO/KNC/DOT pilot uses12sources. v004 captured all12 in81.828s;ALGO passed,
  KNC date wording/DOT ratio wording failed. Saved bodies support equivalent
  exact clauses;new v005 plan records corrections and predecessor source hashes.
 12verified captures copied into v005 cache;v004 proofs/config remain unchanged.
- v005 cache-only pilot passed all3 cases in60.156s,zeroHTTP. Final v006 only
  defers the3 explorer URLs to last;assertions unchanged,verified cache reused.
  Final v006 pilot passed all3 in46.656s,zeroHTTP,23in-scope candidateweeks;
  all output hashes identical to v005. Final215tests/Ruff lint+format passed.
- Separate v006_offline full smoke passed45.375s,zeroHTTP:81unique records,
  18additional cases/59sources,all3hashed replacements accepted,baseline22of40
  supported retained. Six old captures available,53notrequested;this is not
  the full acquisition result. Its outputs cannot be upgraded in place;usev006.
- Full18 acquisition completed by user:31of40history candidates supported,
  33corroborated overall. Nine remaining history candidates still pending;all81
  retained. Baseline22of40 comparison is preserved,not the current count.
- Run inWSL:conda activate funding-strategy;then
  python scripts/run_early_identity.py run --fetch --version v20261119_006
  python scripts/run_early_identity.py summary --version v20261119_006
  First full fetch estimate3–8minutes,network dependent. Result:
  data/interim/early_identity_all/v20261119_006/full/summary.json;
  log reports/acquisition/early_identity_all_v20261119_006.log.
- See docs/UNIFIED_EARLY_IDENTITY.md and REMAINING_EARLY_IDENTITY_PROTOCOL.md.
  No paid data/keys,canonical joins,factors,labels,fit,PnL,orOOS access. Size
  vintage,lifecycle/specs/paidfunding remain unresolved. Next task:inspect full
  acquisition summary and exact pending gates;register follow-up only as needed.

## Completed unified81-identifier processing tool (preserved baseline)

- User confirmed scope81early IDs,not924. docs/UNIFIED_EARLY_IDENTITY.md;
  scripts/run_early_identity.py;registry config/early_identity_all_20261119.json.
  One command:python scripts/run_early_identity.py run --fetch. summary checks
  exported report hashes. No more eight-case scripts or recursive old runners.
- Shared54raw/parsed snapshots and81daily panels verified once;old24batch rules
  recomputed with frozen pure helpers and matched exactly. Four base/supplement
  rules reproduced;source/code/config/dependency/predecessor hashes checked;
  primary IOTA evidence rechecked. Old batch outputs not rewritten.
- Full v20261119_003 completed39.234s,81rows/862candidateweeks/zeroHTTP. Statuses:
 24corroborated identity,4registered-pending,52need source assertions,1indexDEFI.
  Of40price-history candidate IDs,22supported;remaining18=3registered-pending+
 15unconfigured. SupportedLEND/AAVE lack120-day2020history. No eligibility claim.
- JSON/CSV81unique IDs reconcile;missing-evidence queue emitted. Identity and
  history separate;all strictflagsfalse. QTUMfunding/IOSTphase limitations kept.
 208tests(11new),newfiles Ruffpass;final same-version replay/report hashes checked.
  v0018-case pilot40.938s/v002full41.063s retained;v003portablepaths/atomicCSV/
  reporthashes/nonempty assertion guards. No gate relaxation or new evidence.
- Outputs data/interim/early_identity_all/v20261119_003/full/{asset_review.json,
  asset_review.csv,missing_evidence.json,evidence_checks.json,summary.json}.
  Log reports/acquisition/early_identity_all_v20261119_003.log. No user rerun needed.
- Additional URLs/cases have no8-case limit:bounded optionalfetch,URLdedup,
  frozen failures,explicit hashed case replacement. Currentadditionalplanempty;
  script completes processing81,not evidence approval81. Changedplan/code needs
  new --version. Windows/WSL bindings portable;one writer/host only.
- Next:register remaining15qualified-case sources/assertions together in the
  additional plan,then one unifiedrun;do not create batch4/5 runner scripts.
  Keep BTC/BCH/ETC/UNI gaps pending;warm-up-zero cases retained. No canonical
  joins/factors/labels/fit/PnL/OOS,new purchases or keys. Sizevintage/specs/cashflows
  unproven. Hypothetical-lag Size join remains a later separately registered task.

## Completed third remaining early identity batch

- docs/EARLY_IDENTITY_BATCH3.md;tool check_early_identity_batch3.py,oldhelpers
  unchanged. Both earlier reviews revalidated;54snapshots/all81daily panel hashes
  checked;original inventory rederived;prior statuses preserved in cumulative queue.
- All8identity rules corroborated:BAT1697,BNB1839,ONT2566,VET3077,IOST2405,NEO1376,
  QTUM1684,THETA2416;214candidate asset-weeks in stated2020scopes. Fixed26sources,
 26newHTTP,5741950rawbytes,errors[]. BAT exact Ethereum address matched to FAQ.
- BNB/VET/THETA pre2020completion clauses pass. No VEN/TFUEL alias,no cap scaling
  or price splice. IOST support-only/native-phase unknown preserved. Later name
  notices/migrations provide identity context,not2020availability or feature values.
- New original QTUM CMS verifies2020Feb20 08UTC locally. Old failed Spanish
  capture and early release flags unchanged.31supplement events still lack proven
  marks/intervals/payments;two prelaunch. No automatic cashflow or phase repair.
- With IOTA/prior batches,22of40price-history candidate IDs corroborated,
 659candidateweeks;18unresolved=3reviewed/pending+15outsidebatches. All81entries
  retained. LEND/AAVE separate,zero120-day2020windows. No tradable-count claim.
- Output early_identity_batch3_20261119/review_001;197tests(7new),newfiles Ruff
  pass;new/prior frozen-source replay0HTTP. No canonical joins/factors/labels/
  models/PnL/OOS. Fullspecs/cashflows/Size vintage/strict eligibility unproven.
- Next bounded batch:ALGO,ZIL,KNC,ZRX,COMP,OMG,DOGE,SXP;register token/name/phase
  assertions first. Keep BTC/BCH/ETC/UNI evidence gaps pending;hypothetical Size
  join later. No purchase or user command needed now.

## Completed second remaining early identity batch

- docs/EARLY_IDENTITY_BATCH2.md;tool check_early_identity_batch2.py reuses frozen
  batch1 pure helpers and revalidates prior review with its unchanged runner.
  All54snapshot/all81daily-panel hashes checked;original queue reproduced.
- All8corroborated:TRX1958,XLM512,ADA2010,ATOM3794,DASH131,XMR328,XTZ2011,ZEC1437;
 246in-scope price-history candidate asset-weeks. Fixed24sources/24newHTTP,
 5814067rawbytes,errors[]. XLM Stellar/Lumens aliases registered beforehand;
  DASH2023/XMR2022 name notices are retrospective identity evidence only.
- Frozen batch1 remains5rules/170weeks,pendingBTC/BCH/ETC. With IOTA,14of40
  identifiers with2020price-history weeks now have corroborated identity rules,
 445candidateweeks.26unresolved=3reviewed/pending+23outside batches. LEND/AAVE
  separate,zero120-day2020windows. All81entries retained;no tradable-count claim.
- Output early_identity_batch2_20261119/review_001 with cumulative81-item queue
  preserving batch1 statuses;new/prior raw/config/tool/dependency/panel bindings.
 190tests(5new),newfiles Ruffpass;new/prior frozen-source replay0HTTP.
- No canonical joins/factors/labels/fits/PnL/OOS;Sizevintage/fullspecs/cashflows
  and stricteligibility remainunproven. No purchase or user command needed now.
- Next bounded batch:BATUSDT,BNBUSDT,ONTUSDT,VETUSDT,IOSTUSDT,NEOUSDT,QTUMUSDT,
  THETAUSDT;register case-specific token/native/migration assertions first.
  Keep BTC/BCH/ETC/UNI evidence gaps pending;versioned hypothetical Size join later.

## Completed first remaining early identity batch

- docs/EARLY_IDENTITY_BATCH1.md;tool check_early_identity_batch.py. Reverified54
  historical raw/parsed snapshots and all81 daily-panel hashes;recomputed full
  inventory equals prior queue. First8 by qualified weeks total273candidateweeks.
- Five identity-only mappings corroborated:ETH1027,EOS1765,LTC2,XRP52,LINK1975;
 170in-scope price-history candidate asset-weeks. LINK exact Ethereum address
  agrees between CMC/official Chainlink docs. No canonical joins or strict eligibility.
- BTC/BCH pending:designated official futures-overview pageHTTP202. ETC pending:
  upgrade title has fullname,body lacks it;body-only gate preserved. BCH allowed
  scope would end2020Nov15 12UTC exclusive;post-fork interval not approved.
-21newHTTP,20raw captures,6980389bytes. Capturecomplete=false retained. Initial
  review_001 kept;review_002 corrects only inline-parenthesis whitespace for LINK.
  No title/related-article fallback,no changed thresholds,no terminal retry.
- All81queue entries retained.40have2020price-history weeks;IOTA plus five this
  batch corroborated;34still pending(3reviewed+31notthisbatch). LEND/AAVE separate,
  zeroqualified120-day2020windows. These counts are not tradable universe counts.
-185tests(7new),newfiles Ruffpass;frozen-source replay0HTTP. Size publication/
  vintage,fullspecs,fundingcashflows unverified;OOSsealed,noPnL/factors/fit.
- Next bounded batch by coverage:TRX,XLM,ADA,ATOM,DASH,XMR,XTZ,ZEC. Retain named
  BTC/BCH/ETC and UNI gaps for separately registered evidence follow-up;then a
  separately versioned hypothetical Size join,not automatic broad approval.

## Completed IOTA and UNI targeted supplement

- docs/EARLY_IDENTITY_FOLLOWUP.md;tool followup_early_identities.py.
  Four fixed sources,4newHTTP,3captured/96469bytes;Binance monthly sourceHTTP202
  frozen. No denial bypass/retry,purchases,canonical joins or OOS performance.
- IOTA1720 historical54snapshots plus official Binance unit CMS/Foundation
  nomenclature pass identity gates.29 named candidate asset-week gaps now have
  a supported alias,not materialized Size joins. Cap scale1;no future supply edits.
- UNI original futures CMS verifies2020Sep18 07UTC,USDT collateral.7083contract
  and official origin/spot name corroborate;4113UNI COIN rejected. Monthly venue
  cross-reference still missing,so registered combined identity gate staysfalse.
- Three identity-only rules pass:IOTA,LEND,AAVE. Remaining833literal leads not
  independently approved. No full specs/cashflows/Size vintage/strict eligibility.
- Output early_identity_followup_20261119_v002/review_002;review_001's legacyHTML
  parser failure retained. Original capture binding retained,new review binds
  parser revision. Prior source captures/reviews and all old releases unchanged.
  Pre-capture namespace stop retained:CRLF conversion of prior script restored
  to exact recorded LF hash. Git attributes now preserve scripts/config LF.
-178tests(7new),newfiles Ruff pass;frozen-source replay0HTTP. No user command.
- Next bounded task:remaining literal identity leads by qualified asset-weeks;
  UNI source remainspending. Then separately register a versioned hypothetical
  Size join;do not claim the entire broad candidate universe is eligible.

## User preference: retain as many defensible assets as possible

- Reconfirmed2026-11-19. Prioritize additional identity/source verification over
  convenient permanent exclusions. Missing evidence means pending,not proof of
  an unusable underlying. Keep raw data and rejection reasons for later recovery.
- Evaluate availability by asset episode and decision date. Exclude only the
  unsupported interval/feature combination;retain supported intervals. Never
  require an asset to survive to the present or have complete future history.
- Keep a broad price/funding/flow candidate universe distinct from the subset
  with defensible Size data. If Size is unavailable,do not fill it with zero or
  silently substitute another feature. Any three-factor comparison is a separate
  preregistered experiment,not a retrospective change to the four-factor baseline.
- Prioritize IOTA's29 named2020 gaps,then UNI futures identity and the remaining
  literal leads. Existing failed captures stay frozen;new evidence requires a
  separately registered follow-up/version. No recovery or eligibility increase
  claimed from this preference update. No purchase authorized or needed now.
- Report both unique candidate assets and per-date eligible counts/asset-weeks;
  never equate a lifetime identifier count with simultaneously tradable assets.

## Completed bounded early Size identity review

- docs/EARLY_SIZE_IDENTITIES.md;tool verify_early_size_identities.py.
  Fixed11sources,8captured including reused LEND notice,10new HTTP requests.
  IOTA project/unit and UNI project pages returned HTTP202;capture complete=false
  preserved,not retried. Review completed=true is not eligibility approval.
- Verified54 historical snapshot hashes and current numeric IDs/contracts.
  Two identity-only rules pass:LEND2239 until2020Oct10 00UTC exclusive;
  AAVE7278 from2020Oct16 07UTC through2020. Shared /aave/ slug cannot replace IDs.
  Cap scale1;no100:1 futures history splice;no canonical joins materialized.
- UNI4113=UNI COIN rejected;7083 contract matches official Uniswap introduction.
  Registered Binance project evidence and futures-specific2020 link unresolved;
  automatic join blocked. IOTA1720/MIOTA proposal likewise blocked locally;
  all29 named gaps remain unresolved despite supportive web-reviewed pages.
- Other833 literal leads not independently approved. Size publication/vintage,
  full specifications,funding cashflows,strict eligibility remain unproven.
  No factors/labels/fits/PnL/OOS;old release/calendar/splits unchanged.
- Output early_size_identity_20261119/review_001;frozen capture failures and
  source/tool/dependency hashes preserved.171 tests(7new),newfiles Ruff pass;
  cached resume checked with0new HTTP. No user command or purchase needed.
- Next:resolve missing sources/UNI futures evidence,or discuss explicit case
  exclusions before a separately registered versioned hypothetical Size join.

## Completed2020 Size coverage inventory

- docs/EARLY_SIZE_INVENTORY.md;tool inventory_early_size.py. Captured54 dates
  (52 Sundays+2019Dec22/29),10800 first-page metadata rows/427 vendorIDs.
  Public data only;53new HTTP total,25042079 raw bytes;full104.61s/errors[].
  Pilot4dates9.906s;resume7.703s/4hits/0HTTP;calendar+Dec27 source reused.
- All81 early identifiers/52 decision dates inspected with verified daily flags.
  74 have literal historical leads,approvedjoins0.862 price-history candidate
  asset-weeks,833 unique literal cap leads(96.6357%);29 gaps allIOTAUSDT.
  Weekly leads min0/median23/max39;29weeks>=20.17weeks havezero price-history
  candidates;first2020May4=3leads,first20 June15,lastDec28=39of40.
- IOTA namedMIOTA/CMC1720 in all54 snapshots,name-only proposal;needsidentity/unit
  verification,no automatic cap scaling. UNI4113=UNI COIN vs7083=Uniswap;
  AAVE7278 vs earlier nameAave/tickerLEND2239 require episode boundaries.
- Other missing literal stems1INCH/AXS/BEL/FLM/SKL havezero121-close weeks in2020;
  first-page absence not nonexistence or proof paid vendor coverage. DEFI index
  excluded. Global cross-date ID changes flagged for review,not future-based masks.
- No purchase justified from post-warm-up gaps alone;first resolve identity,
  then versioned hypothetical7d-lag/7d-expiry join. Publication/vintage unproven,
  strict eligibilityfalse. No factors/returns/labels/fits/PnL/OOS or olddata edits.
- Output early_size_inventory_20261119/full/{weekly_coverage,asset_review_queue,
  summary}.json and captured metadata.164tests(7new),newfiles Ruff lint/format
  pass;output hashes/counts independently reconciled. No user command needed.

## Completed separate2020 research release

- docs/EARLY_RESEARCH_RELEASE.md;tools build_early_research.py/early_research_rules.py.
  Shared canonical/binance_um_early_research/v20261119_001/ built85.578s/errors[].
  81 identifiers,1526 verified source partitions,1527 normalized partitions:
  trade344043/mark346321/funding43058 rows;QTUM supplement31;daily29646 rows.
- Each daily/{symbol}.parquet has366 data days;raw compatible observations have
  source metadata/decimals and extra typed flags. Empty-day prices/volume sums
  null;no price fills,factor values,forward labels,models,PnL or OOS performance.
  Frozen924 inventory retained as file-presence annotations,not924 daily series.
- QTUM31 missing intervals/event marks remainnull;pre-proposed-launch2 flagged,
  HTTP202 source gate unresolved. DEFI composite-index flag;LEND settlement and
  separate AAVE launch applied only here. Raw quarantinecounts trade753/mark1299/
  funding6;rows retained,not automatically considered unpaid. Unknown origins kept.
- Source verification,atomic roundtrip outputs,hash-bound per-symbol resume.
  Six-name pilot143 sources/144 outputs/2196 daily rows16.625s;resume6hits11.109s.
  Real observation reader integration and full output hash/count/schema checks
  pass.157 tests (9new);new files Ruff lint/format pass;native3.11/Arrow11.
- Historical Size,publication/event-price/cashflow/strict eligibility unproven.
  2019 samples not integrated;old2021 releases/warm-up flags,calendar and approved
  splits unchanged. Early Size inventory subsequently completed above;identity
  checks/join and remaining2019 coverage/combined-history plan still pending.

## Completed targeted checks with QTUM source gate unresolved

- docs/EARLY_CASES_REVIEW.md;tool check_early_cases.py/config early_cases_20261119.
  Four fixed official URLs:3 captured,QTUM launch pageHTTP202;no alternatehosts
  or retries. Initial capture/reviewsuccess=false preserved. review_002 freezes
  terminal failure and binds source hashes;two reruns0HTTP. No user command now.
- QTUM query32 observations inclMarch1 sentinel;31 February rows recovered,
  exact Decimal March1 rate matches checksum-verified archive. All31 lack mark
  price and API-reported interval. Before proposed launch2 events:Feb19 16:00,
  Feb20 00:00. No inferred8h/cashflow;exact launch clause only web-reviewed,
  local capture unverified. Summary staysfalse for that outstanding source gate.
- Official CMS verifies DEFI composite index/not separate token,launchAug28
  2020 07UTC.3 earlier funding events quarantined from live-payment inference;
  cannot join a same-ticker standalone token Size. Source rawtext/hash preserved.
- Official CMS verifies LEND futures settlementOct10 2020 00UTC,AAVE futures
  launchOct16 07UTC;November zero-volume artifacts post-settlement. Retain prior
  LEND history separately;100:1 spot swap does not splice futures prices.
- Two declarative early-window decisions stored,not executable masks or applied
  to old releases. Existing2021--2026 release/calendar/training/OOS unchanged.
  Publication/vintage,funding cashflows,exact event prices/readiness stillfalse.
- 148 tests pass (7new),new files Ruff lint/format pass. No returns/fits/PnL/OOS.
  Early normalization/masks subsequently completed above;Size/identity/2019
  coverage pending. Unsupported QTUM capture/nullable fields preserved.

## Completed early RAW download and independent audit

- User download succeeds:1526 files/24153565 bytes,1520 downloads/6 hits/errors[].
  Independent offline audit verifies all raw/checksum/provenance bindings and
  recomputed CSV quality in47.36s. docs/EARLY_HISTORY_AUDIT.md has exact findings.
- All154 incomplete hourly files are boundary-only;865 complete,zero within-file
  interior trade/mark gaps. Boundary geometry is not proven listing/settlement.
- LENDUSDT2020-11:225 constant-price/zero-volume rows,no positive trade. Preserve
  as inactive-artifact diagnostic,not usable history. Bar-month funding mismatches
  November/December remain;do not fabricate payments or delete other history.
- Funding507 files/43027 events,reported8h across81 identifiers;no intervalchanges
  or spacing flags>1000ms;maxsmalloffset45ms. No interior funding archive-month
  gaps,but QTUM2020-02 leading archive absent (trade Feb20,mark Feb19,fundingMar1).
- DEFI3 funding events Aug27 08:00:00.010/16:00,Aug28 00:00UTC precede first
  available markAug28 04:00/trade07:00. Need episode review,no inferred payments.
  Other43024 events have same-hour mark bars,not proven exact event prices.
- funding_cashflows_verified/exact_funding_event_mark_prices_proven/readiness
  stayfalse. No returns/fits/PnL/OOS inspection,HTTP or source overwrites.
- Tool audit_history_extension.py;ignored early_history_audit_20261119/full/.
  Pilot72 files2.313s,resume72hits2.516s. 141 tests pass (7new),new files Ruff
  lint/format pass. Targeted checks subsequently completed above;normalization
  and earlier Size/identity/2019 coverage pending. No user command for this audit.

## Early-history/funding extension before portfolio experiments

- User authorized backfill toward2019 and associated funding inputs;hold portfolio
  specification while data work proceeds. docs/HISTORY_EXTENSION.md has findings
  and tested WSL command. Existing release/calendar/training/OOS unchanged.
- Tool extend_usdm_history.py verifies924 identifiers/2772 cached listing jobs,
  full pagination/URL/hash integrity;97.688s,zero metadata HTTP. Reparsed old
  66893-file/1035606342-byte totals match frozen census. No old tools modified.
- Frozen archive evidence has no2019 monthly files;2020 extension1526 files/
  24153565 bytes/81 IDs:trade509,mark510,funding507;zero checksum gaps.
  Monthly three-series file presence11 Jan/30 Jun/80 Dec,not eligible counts.
- BTC/ETH January2020 six-file pilot124307 bytes passes;resume6 hits/0 downloads.
  Full extension subsequently downloaded by user and independently audited above.
  No rerun needed;raw success is not eligibility or verified funding cashflow.
- probe_2019_history.py made3 bounded BTC2019-09-14 API requests,allHTTP200:
  trade1bar,mark0,funding2events with missing markPrice. Sample availability only;
  full2019 coverage unproven. Cached evidence retained,no retries/alternatehosts.
- Funding archive/bar mismatches queue163 identifiers over2019--2026-10;not
  proven missing settlements. Need interval/time/unit/sign/event-price/terminal
  reconciliation;hourly mark cannot silently substitute for exact event mark.
- 134 tests pass (13 new),new files Ruff lint/format pass. No model/returns/PnL/
  OOS performance. Next raw backfill,normalization,funding/early Size/identity
  checks;training extension needs protocol amendment,not silently edited dates.

## Completed full weekly coverage

- User WSL full scan succeeds7.979s,924 IDs/209 dates/errors[];local count artifacts
  checked. Assumed-Size candidates0/102/142 min/median/max;192/209 weeks>=20.
- All17 below20 are2021-01-04..2021-04-26 with zero price/funding candidates,
  consistent with120-day warm-up. First passing2021-05-03:68 assumed-Size.
  2023 min99/median120/max131;2024 min112/median133/max142.
- 2022-08-01 is the only post-warm-up week below50:29 assumed-Size,44 price/
  funding;cause unresolved. Do not infer liquidity or Size-only explanation.
- No returns/labels/fits/PnL/OOS performance inspected;strict eligibility false.
  Next specify holdings/exposures,features/model/refit,cost/funding/terminal gates.

## Latest weekly baseline stage 0 and coverage handoff

- Registered experiments/001_weekly_baseline_stage0.md + machine-readable
  config/weekly_baseline_v1.json before implementation. Tools weekly_contract.py
  and check_weekly_baseline.py;docs/WEEKLY_BASELINE_STAGE0.md has full command.
- Research assumptions:Monday00UTC cutoff,01decision,01--02hour VWAP entry/
  next-week exit,exit-end+1h assumed label availability. Label later is simple
  seven-day proxy return before costs/funding. No values computed. These are
  not verified exchange publication latency or actual fills.
- 209 development dates;round1 train103/validation51 time-only usable,round2
  train155/validation52;one boundary purge per period. No2025+ projected rows,
  no prices/returns/PnL/modelfit;strict Size/readiness remainfalse.
- BTC/BNX/SUN pilot passes15.422s,resume13.125s/3hits;assumed-Size counts
  min0,median1,max2 in this subset only. Full924 scan subsequently completed
  by user;results above. No rerun required for this result review.
- 121 tests pass (10 new);changed-file Ruff lint/format pass. Native3.11/Arrow11.
  Holdings/models/refit/costs/funding/terminal and performance gates pending.

## Approved weekly research sequence

- User approved docs/WEEKLY_RESEARCH_SEQUENCE.md:one-week prediction/weekly
  portfolio baseline,independent rank-buffer experiment,then position adjustment.
  Stage0 fixes target/clock assumptions;20/60/120 sizing remains a candidate.
- Isolate buffer on the same schedule;daily monitoring is a separate frequency
  comparison. Separate resizing turnover from membership changes. Later sizing
  needs comparable exposure/risk;do not credit lower exposure as signal quality.
- Literature anchors recorded with version limits. No performance/fit/OOS run.
  This direction record is not the complete preregistration;fees,universe,
  holdings,models,refit and numerical acceptance thresholds remain to resolve.

## Approved split and user-reported full build

- User approved docs/RESEARCH_SPLIT.md:train2021-22/validate2023;
  train2021-23/validate2024;sealed final OOS2025-01 through2026-10,all UTC.
  Trailing pre-boundary history allowed;overlapping training labels excluded.
  Exact sample endpoints await target/execution timing;no random row split.
- Full WSL build reported successful:223.383s,errors[],924 IDs/1968120 rows/
  66893 source partitions/244 legacy BNX hours. Ever-passing diagnostics787
  price/funding,338 assumed-Size four-factor,338 class-review-clear,0 strict.
  Not simultaneous tradable counts;readiness/strict Size vintage remainfalse.
- No strategy performance/OOS inspection. Weekly target/clock fixed for stage0;
  refit and complete trading protocol remain pending.

## Latest daily-input implementation and handoff

- docs/DAILY_RESEARCH_INPUTS.md has the full WSL command and expected manifest;
  scripts/build_daily_inputs.py + daily_input_rules.py build new immutable daily
  sidecars. No factor returns/labels/fit/PnL, downloads or OOS performance viewed.
- Fixed five-identifier pilot passed:759 daily rows,102 source partitions verified,
  244 legacy BNX hours consumed;267 post-close archive hours excluded. Initial
  17.328s;verified resume11.031s/five hits. Source releases remain unchanged.
- Per-row episode resets,24-hour completeness,121-close history vs20/60/120
  endpoints,strictly earlier same-episode funding and scoped policy enforced.
  Unknown lifecycle/settlement accounting remain unresolved;no final universe.
- Size uses separately labelled diagnostic snapshot-end+7d availability/7d expiry.
  Publication/revision vintage is unproven;strict eligibility/readiness stayfalse.
  Pilot distinct candidates:price/funding3,assumed-Size four-factor2,strict0.
  Current classifications are ex-post annotations,not a causal universe.
- 111 tests pass;new builder/rules/tests Ruff lint/format pass. Native3.11/Arrow11;
  configured project3.13. Full daily build subsequently run by user in WSL Conda.
  Expected924 IDs/1968120 rows/66893 source partitions,not924 tradable assets.
- User supplied full manifest;calendar splits now approved above. Label overlap
  details and the remaining strategy protocol still precede experiments.

## Latest completed full-universe retention screen

- User clarified: retain as many usable assets as possible, not maximize exclusions.
  All924 IDs screened;923 have some files,922 positive-volume trade observations.
  GAIB has mark/funding but no trade;LEND has no files. No whole-history deletion
  for a local gap/stub/current classification;all raw/research releases unchanged.
- docs/FULL_UNIVERSE_RETENTION_SCREEN.md; tools scripts/screen_full_universe.py
  and scripts/export_screen_candidates.py. Full22635 trade acquisition reports
  validated in91.391s;zero errors. Trusts prior raw checksum audit,not fresh ZIP
  or every-Parquet/hourly-close verification. No downloads/OOS performance viewed.
- 426 Size-history ID leads after component blocks;405 have potential overlap
  with an active month. These are contract identifiers,not necessarily distinct
  crypto coins,simultaneous holdings,valid daily joins or a final universe.
  789 have possible120-day elapsed span only;episode resets/gap-free closes not
  validated. None of these cohorts necessarily has the same membership.
- 149 identifiers with stub months retained in other months. KNC/DYDX/MDT still
  Size-blocked,8 scoped restrictions attached for later row-level application.
  Current239noncoin/30missing metadata not automatic historical exclusions.
  405 Size-month leads include22 missing-current-metadata names;NUUSDT is the one
  current-noncoin annotation requiring identity/episode review within this cohort.
- Ignored data/interim/full_universe_screen_20261118/: quick/review_queue.json;
  full/checkpoints,indexes,yearly_instrument_month_counts,summary;exports/ named
  candidate_lists.json and enriched review_queue.json. All924 checkpoint hashes
  and cohort/report counts reconciled by exporter. No user command needed.
- Five-asset pilot248 reports1.016s;resume5 checkpoint hits0.421s. Full run executed
  because pilot was fast;no remaining full metadata scan handoff. Initial loader
  ledger/file-population assumptions fixed;failed logs preserved,final full passes.
- 99 tests pass (6 new);new scanner/exporter/tests Ruff lint/format pass. Native
  Python3.11;configured runtime3.13. Existing unrelated native import-order lint
  unchanged. Formal eligibility/automatic joins remain false;no factors or PnL.

## Previous completed identity follow-up

- User authorized checking and conservative exclusions where identity/specification
  evidence cannot be established. Exclusions are ex-post data-join restrictions,
  not a certified causal universe. Preserve raw data and reasons; missing Size
  alone does not prove nontradability. No strategy performance/OOS inspection.
- Findings: docs/IDENTITY_FOLLOWUP_DECISIONS.md. Sources/query log:
  config/identity_followup_sources_20261118.json; policy:
  config/identity_decisions_20261118.json. Tools: scripts/check_identity_followup.py
  and scripts/build_identity_decisions.py. Ignore generated data artifacts.
- All27 priority cases decided:24 retained identity candidates,3 temporary whole
  Size-join exclusions (KNCUSDT,DYDXUSDT,MDTUSDT),8 interval/scope restrictions.
  Retention is NOT join/trading approval. KNC/DYDX futures switch evidence remains
  unestablished; MDT legacy mapping unresolved and later episode is equity.
- SUN launch verified2024-08-22 13:05UTC, after2021 spot migration. CMC10529 full
  Tron address matches official migration source; discard old6990 association for
  this contract. Prior futures-migration concern corrected, old report preserved.
- SATS/1000SATS same-asset denomination supported by cached official rendering;
  direct bundle page now404. Preserve excerpt/provider limits. Primary historical
  candidate28683; alternate28194 NOT automatically spliced; no USD cap scaling.
- Baby Doge case-sensitive lookup corrected:CMC10407 has61 captured snapshot
  dates (not61 tradable observations). BOB34422,CAT32724,rats28452,WHY30867,
  X33108 current IDs identified but have ZERO dates in captured first-page history.
  Missing Size treatment/data requirement remains; no automatic whole-asset drop.
- BNX7 existing raw/normalized partitions verified by checksum/hashes/times/counts.
  Late2025-04/2026-10 trade is fixed-price/zero-volume; sampled mark is also fixed.
  March2025 settlement-hour positive bar is NOT proven executable after closure.
- BNXUSDTSETTLED official listing and February2023 ZIP/checksum verified:
  511 rows,244 positive-volume legacy hours,267 post-close zero-volume rows.
  Current BNXUSDT February starts at new relaunch; legacy hours NOT integrated.
  Relaunch-hour bucket14:00 does not prove trading before14:45 launch.
- Ignored root data/interim/identity_followup_20261118/: final audit_003/ and
  decisions/. Earlier audit versions retained.17 source URLs:15 success,one404,
  one REST probe exhausted3 failures; raw7,336,544 bytes. Capture success=false
  is preserved; bounded audit and decisions succeeded. Do NOT retry REST/downloads
  merely to turn this flag green. No access denial bypass, keys or purchase.
- 93 tests pass (9 new); new scripts/tests Ruff lint and format pass. Native
  Python3.11/Arrow11; configured runtime3.13. Existing unrelated native full-tree
  import-order lint in tests/test_research_data.py unchanged. No final universe,
  automatic historical joins, factor/label/fit/PnL or orders; readiness stays false.

## Existing releases and evidence

- Shared canonical/binance_um_research/v20261117_001/:66893 partitions;
  trade16217181,mark16418784,funding2811083 (total35447048); overlay33168.
  User built successfully in WSL funding-strategy Conda. Original source/lifecycle
  hashes unchanged; embedded lifecycle remains21 sources/47 events.
- Supplemental lifecycle_review_20261118/ + config/lifecycle_facts_20261118.json:
  52 sources,91 events,64 IDs;61/61 priority IDs have partial evidence,zero full
  lifecycles. Ex-post only,causal_available_at=null. Never silently attach to old
  release. Known LIT/PUMP/MDT reuse; PumpBTC settles2025-06-13 09UTC, relists as
  PUMPBTCUSDT10UTC; laterPUMP is Pump.fun. OMG final close2025-01-31 09UTC;
  DOTECO is index. Details in LIFECYCLE_REVIEW.md and evidence configs.
- Full CMC acquisition305 dates/61000 rows/662 IDs,zero errors,151839940 raw bytes;
  four-date resume zeroHTTP. Root cmc_weekly_20261118/. No repeat download.
  PlanSHA8dd8dd5bde3736138e1efb29ab3915222266cc5d9cd418700ed99cc3d6e6cb46.
- Audit merge70e06ef: cmc_identity_audit_002_20261118/ verified all raw/parsed;
  924 identifiers,418 literal candidates,506 absent,9 multi-ID histories,16 scaled
  flags,23 raw-symbol variants. GAIB/LEND missing trade bounds retained. All61000
  cap rows have unproven availability/vintage. Annual archive-month lexical proxy
  includes noncrypto/scaling and is NOT usable Size coverage or a buy-data metric.
- Evidence merge048e962:39 official captures,41 assertions,35 proposed episodes;
  25 vendor-ID proposals. config/contract_identity_evidence_20261118.json;
  contract_identity_review_20261118/review_002/. Source bytes preserved; follow-up
  decisions supersede listed unresolved SUN/Baby/SATS proposals only as documented.
- Readiness mergeee9f94d: Coin Metrics32 BTC/ETH observations/135 IDs; current
  issued-supply cap differs from CMC circulating cap. Funding11 partitions/969 rows;
  12 API events match rate/time but markPrice empty,max boundary offset20ms.
  106 post-captured-close flags are ex-post,not proven cashflows. Actual settlement
  notional/prices,ordering,terminal accounting and source availability unresolved.

## Preserved limitations

- Raw66893 ZIPs/1035606342 bytes provenance/checksum verified.924 identifiers are
  not924 crypto assets; current655COIN/239nonCOIN/30absent are annotations only.
- Mark recovery33168/33240 keys;four common gaps33096 hours covered;72 unresolved
  over7 IDs,70 also trade. Partial canonical mark release unchanged. Trade424
  interior hours/13 files,1913 constant zero-volume files. Funding month gaps
  BNT27/BTCST1/LIT5/MDT15;CVX/SLP/LIT archive/announcement timing conflicts remain.
- Old exact12 pilot actually11, original lifecycle gate and legacy duplicate BTC
  missing Parquet remain FAILED. Reconciliation589db70 verified9 other Parquets/
  183 rows;no waived gaps,zero filling or silent gate upgrades.

## Research decisions still deferred

- Candidates:momentum20/60/120,Size,funding,taker imbalance. Rank buffer accepted;
  SHAP required. Equal composite baseline/LightGBM challenger discussed; NLP later.
- Weekly baseline target/clock assumptions registered;holdings,buffer,
  costs,refit and acceptance gates NOT frozen. Nautilus proposed,not installed.
- User reports no2025-26 performance tuning. Final OOS2025-01..2026-10 calendar
  approved and sealed;full protocol not frozen. Liu/Tsyvinski2021 note docs/literature/liu_tsyvinski_2021.md;
  appendix absent. Conditional means are not executable cross-sectional spreads.

## Next bounded segment

1. Verify IOTA/MIOTA and UNI/AAVE/LEND identity episodes,then versioned early Size
   join;consider paid data only from residual qualified gaps. OOS remains sealed.
2. Measure Size availability in a separately justified historical universe; decide
   missingness treatment or paid data from actual deficits. Do not restart open-
   ended KNC/DYDX searches without specific new evidence or select by future data.
3. Finish lifecycle/specifications/funding/terminal accounting, then freeze the
   strategy/OOS protocol before simulation/development experiments. Final OOS only
   after final version is frozen;paper/live discussion after OOS review.

Original daily build/weekly coverage and early RAW audit complete. Never run Windows and
WSL writers concurrently; local locks do not coordinate hosts. No secrets/datasets
committed; reusable tools remain in repo.
