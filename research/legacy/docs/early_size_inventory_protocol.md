# Early historical Size inventory

Registered2026-11-19 before implementation. User requested coverage inventory,
not purchases or a strategy experiment. Scope81 early archive identifiers and
2020 weekly/daily source availability. No paid accounts/keys,returns,labels,
model fitting,PnL or OOS performance. No old release/approved split changes.

Source calendar:hash-verified existing CMC public historical index.54 dates:
52 Sundays in2020 plus2019-12-22 and2019-12-29 carry-in. Fetch only first public
page per date;reuse verified2020-12-27 and calendar evidence. Maximum raw budget
64MiB,2MiB per response,single stream with2s pacing;existing downloader's bounded
retries/access-stop rules apply. No pagination/alternate-host bypass or claim
of all-asset coverage. Retain raw evidence but parse only identity,cap and supply
fields,no price changes/performance. Verify a4-date pilot(20200105,20200503,
20200830,20201227),resume,then full54-date inventory if source access succeeds.

Map using each historical snapshot's literal case-insensitive token symbol
against the contract stem,not today's baseAsset or future membership. Same-date
multiple-ID matches remain ambiguous. Single literal matches are unverified
leads,not approved identity joins. Aggregate name-only suggestions/ID changes
for manual review;never automatically splice IDs,rename tokens,scale USD caps,
apply future classifications or fill outside captured coverage. DEFI composite
index is excluded from single-token Size leads;preserve its source identifier.

For coverage only,use the previously declared snapshot-day-end+7d availability
and7d expiry assumption. Select the latest globally available captured snapshot;
do not revive an older asset cap if missing in that snapshot. Publication and
revision vintage remain unproven;strict Size readiness staysfalse.

Read only hash-verified early daily quality flags. Report52 Monday decision
dates,all81 identifiers' raw/same-date literal coverage,and per-week intersections
with valid closing activity,121-close price-history diagnostics,and optional
fresh-funding diagnostic. The latter is not a verified four-factor strategy pool
or proof of valid taker inputs/cashflows. Preserve warm-up/empty weeks in totals.
Pilot coverage is partial and must not be represented as full-week coverage.

Acceptance:all54 dates listed in frozen source calendar;exact date title and
source/parsed hash agreement;uniform metadata-only fields;all81 panel source
hashes bound. Full report includes exact observed row/ID counts,missing dates,
weekly min/median/max,per-instrument missing/ambiguous/name-only review leads.
No target coverage percentage or profitability threshold imposed after results.
Synthetic tests for calendar,lag/expiry,partial coverage,same-date ambiguity,
future-ID leakage,index exclusion and source/output integrity. Successful resume
must makezero new HTTP requests. Missing source access remains a visible gate.
