# QTUM funding recovery and DEFI/LEND episode review

2026-11-19. Registered on main at `8df66d7`:
[early_cases_protocol.md](early_cases_protocol.md).
Tool:`scripts/check_early_cases.py`;config:`config/early_cases_20261119.json`.
This bounded check is finished with one unresolved source capture. No old raw,
canonical,policy,training or OOS release changed;no fit/returns/PnL inspected.

## QTUM observations recovered,not proven paid

One bounded official funding-history query returned32 observations:31 in
February2020 and one atMarch1 00:00UTC. The March1 rate matches the independently
checksum-verified March archive using exact Decimal comparison. Query bounds,
symbol,monotone unique timestamps,finite source decimals and unsaturated limit
validated. February observations retained separately,not inserted into old data.

Two observations,February19 16:00 andFebruary20 00:00UTC,precede the proposed
February20 08:00 launch boundary. They are explicitly flagged,not discarded or
called payable fees. All31 February events lack both an associated markPrice
and an API-reported funding interval. Observed spacing is not a historical
published schedule;do not assign8h merely because the March archive reports8h.
Exact settlement price,publication time and funding cashflows remain unproven.

The [official Spanish launch page](https://www.binance.com/es-LA/support/announcement/detail/360039972971)
was visible in web search with the dated clause,but direct raw capture returned
HTTP202. The English legacy URL displayed no article. Local machine verification
of the exact QTUM launch clause remainsfalse. Preserve this limitation and
`success=false`;do not change a failure to green from the search excerpt alone.

## DEFI is an index contract

Captured official CMS content verifies launch2020-08-28 07:00UTC and explicitly
states DEFI is not a separate token ticker. The3 funding observations before this
launch cannot be assigned to an already-open live position in the contract.
Retain raw evidence and quarantine from prelaunch payment/trading reconstruction.
Do not map the composite index to a same-ticker token's market capitalization.
[Official announcement](https://www.binance.com/en/support/announcement/detail/ebee6da5df3946519fdb9ab27706d1a4).

## LEND settlement explains late inactive artifacts

Captured official CMS content verifies perpetual automatic settlement/delisting
2020-10-10 00:00UTC and AAVEUSDT launch2020-10-16 07:00UTC. Thus LEND's November
constant-price/zero-volume rows occur after the documented settlement. Preserve
them,but do not use them as active trading history or invent post-settlement
funding. Earlier LEND observations are not dropped wholesale. The100:1 spot
token swap does not splice two closed/new futures histories.
[Official notice](https://www.binance.com/en/support/announcement/detail/17595222999545348c8acdd5dc41c00a).

Two declarative episode decisions are stored for the early window through
2021-01-01 only. These are ex-post review facts,not executable universe masks;
the next normalization implementation must translate and test the boundaries.
Existing2021--2026 releases were not silently reclassified. Current captured
article content does not prove historical revision/publication availability.

## Evidence,partial gate and verification

Root:`data/interim/usdm_universe/early_cases_20261119/`:

- `raw/`:3 verified sources and the HTTP202 attempt;four source HTTP requests,
  27,285 total evidence bytes. Initial `capture_summary.json` remainsfalse.
- Initial root review artifacts preserve the partial result. `review_002/`
  adds frozen terminal-failure reuse and hashes,without retryingHTTP202.
- `review_002/qtum_february_observations.json`,`march_overlap.json`,`facts.json`,
  `decisions.json`,`summary.json`. Summary remainsfalse solely because the exact
  QTUM launch clause is not locally verified.3/4 sources verified;2 episode
  decisions;cashflow/eligibility flagsfalse.

Two verified review reruns madezero source HTTP requests. No alternate host or
endpoint was used to bypass the HTTP202 response. Failed evidence is integrity-
checked and frozen for this review. Reproducible summary:
`python scripts/check_early_cases.py summary`;no user run is needed now.
Log:`reports/acquisition/early_cases_20261119.log`.

148 tests pass (7 new),changed-file Ruff lint/format pass. Tests cover exact
decimals,bounds,duplicates/order,saturated response,missing mark/interval,overlap
mismatch,article identity/clauses and terminal-failure integrity/no retry.

Next:versioned early normalization with explicit unsupported-payment masks and
unknown fields,then historical Size/identity/2019 coverage. Do not claim the31
observations or two notices resolve all lifecycle or terminal accounting gates.
