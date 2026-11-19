# Early observation release and daily panel protocol

Registered2026-11-19 before implementation. User authorized building the new
early research data version. Scope2020-01-01 through2020-12-31 only;2019 remains
partial API evidence,not a completed series. Preserve old releases and approved
training/validation/OOS windows. No HTTP,model,returns,factor scores,labels or PnL.

Inputs:1526 checksum-verified monthly archives over81 archived identifiers,
independent early audit,and QTUM31 February API observations with March sentinel
agreement. Capture/reviewsuccess=false for the HTTP202 QTUM announcement remains
visible. It is not waived;QTUM proposed launch is an unverified diagnostic only.

New release:shared `canonical/binance_um_early_research/v20261119_001/`.
Keep compatible observation fields and raw decimal strings;attach row-level
policy flags and unknown publication fields. Funding interval/mark from the API
remain null;do not infer8h,zero fees or exact event prices. Do not insert the
March API sentinel,which already exists in the archive. Expected1527 partitions
and43058 funding rows (43027 archive+31 supplement),without duplicate events.

Confirmed DEFI launch2020-08-28 07UTC/composite-index identity,LEND settlement
2020-10-10 00UTC,and separate AAVE launch2020-10-16 07UTC apply to this early
version only. Preserve/quarantine prelaunch/postsettlement observations;do not
join index Size to a same-ticker token or splice LEND/AAVE prices. Retain unknown
lifecycle status for other instruments. All historical strategy/payment
eligibility flags stayfalse;these flags are ex-post review,not causal signals.

Add a daily long panel for the81 observed identifiers,366 data days each:
29646 rows. Include closes/raw strings,hour counts,volume/taker totals,latest
strictly earlier funding observation and its age/nullable interval,known-event
and unverified-boundary flags,separate20/60/120 endpoint/121 contiguous valid
close diagnostics. No missing bar insertion or forward-filled prices. A partial
first trading day may supply a valid closing observation but is not a complete
24h day. A zero-activity day cannot extend valid closing history. Publication
timestamps remain unknown;next midnight is only a reference,not a trading clock.
No historical Size is integrated by this release;record this explicitly.

Acceptance:all input/output/source hashes bound;reverify source integrity and
CSV quality;fail closed on conflicts. Fixed schemas must preserve nullable
fields across partitions. Parquet round-trip equality,exact input row counts,
31 supplement rows,81 daily series/29646 rows and safe verified resume required.
Test unknown interval/price,confirmed versus proposed boundaries,LEND/AAVE
separation,prelaunch quarantine,latest-event cutoff,history gaps and output
corruption. Pilot BTC/ETH/QTUM/DEFI/LEND/AAVE,then full local build if modest;
otherwise hand off a tested full command. Preserve failed gates and original
raw data. No readiness upgrade merely because conversion succeeds.
