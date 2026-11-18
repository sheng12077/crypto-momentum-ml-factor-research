# Early-history raw and funding audit

Registered2026-11-19 before implementation. Follows the completed1526-file
extension acquisition,not a strategy experiment. No downloads,returns,fits,PnL
or OOS performance inspection. Original releases and split rules unchanged.

Expectation: independently verify the acquired2020 files and distinguish month
boundary truncation from interior hourly gaps;describe observed funding time
and interval consistency without claiming missing/payable settlements.

Acceptance: verify all1526 plan/report/ZIP/checksum/provenance bindings and
24,153,565 bytes;fresh CSV quality must exactly match acquisition reports. Any
integrity or structural mismatch fails closed. Classify the154 incomplete hourly
files from evidence rather than prescribing boundary/interior counts. Preserve
the zero-volume artifact and every gap;do not fill or exclude whole assets.

Funding: require finite rate and positive integral reported interval;retain exact
timestamps. Compare successive events across months for each symbol. Report
interval changes separately. For stable reported intervals,abs(delta minus
reported interval)>1000ms is an inspection flag,not proof of a missed settlement;
also report maximum offset within1000ms. Do not round timestamps to an8h grid.
Flag missing funding archive months against bar archives and identify whether
funding and mark bar coverage coincide;hourly mark bars do not prove exact
settlement mark price. Terminal events and publication availability stay unproven.

Implement a reusable integrity-checked offline auditor with per-file checkpoints,
synthetic tests for boundary/interior gaps,invalid intervals,cross-month jitter,
source corruption and host-independent cache paths. Pilot BTC/ETH first,then
full local audit if modest. Bind tool/dependency/source hashes,verify resume.
Success means completion of this raw audit,not historical eligibility. No
revision of thresholds after results;report deviations or failures explicitly.
