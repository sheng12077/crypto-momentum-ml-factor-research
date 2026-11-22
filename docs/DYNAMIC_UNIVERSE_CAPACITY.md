# Dated candidate-pool capacity — Experiment 019

Registered before implementation in[Experiment019](../experiments/019_dynamic_universe_capacity.md).
This checks whether temporary date-specific exclusions leave a useful candidate
population. It is not a strategy backtest or a certificate of execution readiness.

## Candidate counts

All924identifiers remain represented on304Mondaydates (280,896rows). The existing
Experiment017history,flow,funding and scope flags are preserved. Additional product
scope is applied only from the current episode's reported onboardDate;current
absence never removes an identifier's history. No fixed37gate,top-Ncap,market-cap
ranking or new liquidity filter is applied.

| Year | Weekly minimum | Median | Maximum | Weeks with at least100 |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 0 | 91.5 | 117 | 23/52 |
| 2022 | 80 | 120 | 135 | 29/52 |
| 2023 | 134 | 159.5 | 196 | 52/52 |
| 2024 | 196 | 241 | 263 | 53/53 |
| 2025 | 267 | 351.5 | 448 | 52/52 |
| 2026 through October | 127 | 500 | 511 | 43/43 |

These are the broader provisional dated crypto-scope counts,not certified tradable
coins. Unknown historical class/episode evidence remains conditional.665identifiers
have at least one such candidate week;that is not the simultaneous pool size.
Early2021includes the120daywarmup of the release startingJanuary2021.
The2022below100dates number23,fromFebruary28throughAugust1;do not force-fill them.

A narrower coverage comparison counts only rows supported by the current COIN
episode metadata from its onboardDate. Its minimum/median/maximum:
2022:68/104/123;2023:123/146.5/183;2024:183/233/260;
2025:264/350.5/446;2026:127/499/511.
Both views stay above100every week from2023onward. The narrower view is a diagnostic
comparison,not authorization to use a survivor-filtered universe. Current metadata
is retrospective evidence,not historical publication/PIT certification. Earlier
crypto episodes of identifiers now tracking equities must not be banned wholesale.

## What temporary exclusion resolves

The prior-only input conditions govern entry candidacy on each decision date.
A candidate exits when its then-observed history/flow/funding/scope fails, and may
reenter when those conditions recover.2026-06-29still has127provisional candidates
after the existing funding-window exclusions. This supports dated exclusion without
permanently deleting hundreds of otherwise useful identifiers.

Verified repair observations are not integrated into this older factor panel;these
counts therefore retain conservative original-input failures,including the disputed
reported-duration rule. No thresholds were relaxed to reach100or200.

The required prior-day daily-close mark is available in the existing+verified-overlay
source union for all provisional candidate rows (zero missing flagged snapshots).
This is only one timestamp per candidate:it does not certify decision-hour/fill,
intraday NAV,funding-payment or terminal marks throughout a held position.

## What temporary exclusion does not resolve

The independent holding audit inspects known same-frequency funding continuity
breaks from bounded source jobs. It does not bridge uninspected months into a
continuous series. It removes nominal gaps with recovered observations and never
asserts an omitted observation was a charged payment. Frequency changes,staleness,
unverified intervals,terminal uncertainty and price execution coverage remain
separate requirements. The audit is not complete funding-cost certification.

Known same-frequency evidence identifies385nominal observation slots,all on
2026-06-24:382at04:00UTC and three hourly slots at01:00,02:00,03:00UTC.
These are source-continuity diagnostics across all checked products,not385proven
missing fees or385tradable crypto assets.

For a hypothetical immediate entry held14days:
-2026-06-15:372of500provisional candidates intersect a known source break.
-2026-06-22:374of502provisional candidates intersect a known source break.

These are potential candidate exposures,not actual portfolio positions or losses.
All such future flags are **excluded from the entry mask**. We cannot retroactively
exit onJune22because an observation is missing onJune24. Excluding new entries on
June29also cannot recover the unknown cost of an already-held position.

A continuous simulation spanning that event still needs independently established
funding treatment or an explicit unresolved/assumption result. An ex-post omitted
period may be reported as a sensitivity analysis,not a deployable escape rule.
Delisting/identity changes and account margin liquidation also need distinct handling.

## Reproduction and artifacts

```bash
conda activate funding-strategy
python -m crypto_factor_research capacity-audit --repair-dir data/repairs/full_universe/9d8e79788ba25d039b37
```

Final ignored output:
`reports/tables/dynamic_universe_capacity/bdd1832d201a3a81105e/`.

-`dated_candidates.parquet`:all924IDs x304dates,entry and separate future-audit flags.
-`weekly_counts.csv`,`yearly_capacity.csv`,`below_threshold_periods.csv`:capacity.
-`asset_dispositions.csv`:all identifiers' dated candidate coverage.
-`known_funding_observation_breaks.csv`:bounded source-continuity evidence.
-`summary.json`:source/config/registration/code bindings,counts and output hashes.

Full build and checksum-verified cache reuse pass.39active tests and package lint
pass,including dated reentry,reused identifiers,absent current metadata,future-gap
separation and sparse-source-window tests. The provisional count is not an economic
capacity/liquidity measure. Execution_ready=false,PnL_computed=false. No new downloads,
canonical overwrite,model fitting or push.

Next work can concentrate on the dated rule definitions,accepted repair integration,
and actual required held/target price/cost/terminal keys rather than forcing every
identifier to be valid for the entire history.100or200is not a prerequisite to a
valid experiment or evidence of profitability by itself.
