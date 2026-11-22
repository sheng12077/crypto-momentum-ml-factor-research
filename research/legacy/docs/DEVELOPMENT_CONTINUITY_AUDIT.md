# Development continuity audit

This is a past-only input diagnostic registered in
experiments/003_development_continuity_audit.md, not a historical strategy run.
It does not fit models, compute labels/PnL or inspect OOS performance.

## What is checked

- All924development daily files are verified against existing indexSHA256.
  Existing2020files are verified in the same way. Values loaded are restricted
  to2020-08-01through2022-12-31;2023onward values are not selected. Full files are
  hashed for integrity, which is not inspection of their strategy performance.
- Weekly decisions are104Mondays from2021-01-04through2022-12-26. Inputs use
  only the prior day's closing information. A120dayreturn needs121consecutive
  daily closes. Gaps, invalid closes, known episode changes and scoped blocks
  reset the numeric chain; no forward fill or ticker alias splice is used.
- The old development history restarts inJanuary2021. The audit separately
  counts rows that would gain enough numeric history from a hypothetical
  early/development join. This is not permission to join identities or trade.
- The proposed aggressive-imbalance input requires seven complete valid daily
  observations. Funding here tests only the old latest-event freshness flag,
  not seven-day event sums or actual settled cashflows. Size is not a factor.
- Existing2020mapping scopes/splice permissions are reported separately and
  never automatically extended. A zero approved count is an evidence/policy
  limitation, not a claim that no instruments were actually tradable.

## Run from WSL

No new download or environment installation is needed. The isolated simulator
environment already contains pyarrow; this checker does not invoke the engine.

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
data/interim/runtime/nautilus313/bin/python scripts/audit_development_continuity.py
data/interim/runtime/nautilus313/bin/python scripts/audit_development_continuity.py --full
```

Default outputs:data/interim/development_continuity/v20261121_001/pilot/ or full/.
The summary records elapsed time, counts, source bindings and output hashes.
Repeating the same command requires unchanged code and inputs and verifies
identical deterministic product hashes. Choose a new --output directory after
changing code/inputs. Source releases are never modified.

| Output | Meaning |
| --- | --- |
| summary.json | Compact readiness and diagnostic counts |
| asset_audit.json | Per-symbol warmup change and existing identity scope |
| weekly_coverage.json | Data-only coverage for all104decisions |
| august_2022_reasons.json | Per-symbol2022-08-01decision failure flags and invalid close dates |
| source_bindings.json | Verified early/development daily/index bindings |
| run_contract.json | Bound code, registration, identity and source hashes |

## Interpretation limits

The924inventory includes identifiers not yet launched in2021–2022. Empty
placeholder days are not missing observations from an active contract. For
Augustfailure analysis inspect trade_hours/mark_hours alongside reason flags,
rather than interpreting all924inactive rows as a venue-wide outage.

Existing base reason bits retain their original semantics from the frozen
daily_input_rules.py. The independent numeric chain is intentionally more
conservative at known partial/scoped days, so it can differ from the old flag
even after the first120days. Do not silently replace the canonical flags.

The early schema has no matching development episode identifier. The year
bridge is explicitly hypothetical; price similarity is not identity evidence.
Likewise, early aggregate taker quote volumes do not recheck every source-hour
base-volume invariant. These are input diagnostics, not certified features or
an approved historical trading universe. Real execution/funding assumptions
and the strategy specification remain separate gates.

## Completed findings (2026-11-21)

Full audit:924identifiers,81earlyfiles,104weeklydecisions,89.515seconds.
All consumed daily files matched their existing index hashes. No downloads,
labels, fitting, PnL or OOS performance inspection occurred.
Full replay took84.547seconds and reproduced all four deterministic output hashes.
New tests10passed;full native regression254passed/1skipped;Ruffpassed.

| Diagnostic | Result |
| --- | --- |
| First2021week, old price/funding candidates | 0 |
| First2021week, hypothetical warmup +7dayimbalance | 49 |
| Identifiers with at least one bridge-dependent decision | 79 |
| Total bridge-dependent asset-weeks | 1135 |
| Hypothetical weekly data candidates: minimum/median/maximum | 44/101/137 |
| Existing mapping covers full lookback and explicitly allows splicing | 0 |

The final zero reflects the scopes/permissions of the existing2020mapping
release. It does not mean that no valid crypto assets existed in2021–2022.
No trading eligibility flags were promoted. For BTC/ETH, numeric history is
available from the first2021week; the old flag first passes on2021-05-01.

### August2022coverage drop

For the2022-08-01decision, the feature day is2022-07-31. Among143identifiers
with at least one trade or mark bar that day,44pass the old price/funding gate.
101have24tradeand24markhours;42have24tradehoursand0markhours. Thus the latter
group has observed trading activity and cannot be classified as inactive simply
because marks are absent. Reason counts overlap:

| Reason among these143rows | Count |
| --- | --- |
| Mark day incomplete | 42 |
| Insufficient/wrong-episode120dayhistory | 58 |
| Missing/wrong-episode funding | 5 |
| Stale funding | 5 |
| No positive trade activity | 4 |
| Known order stop | 2 |
| Scoped execution block | 1 |

Independent canonical-hourly BTC check:July2022tradehas744rows,including24on
July31;markhas720rowsandendsJuly30at23:00UTC. This is a month-end mark gap in
the consumed canonical release. The old recovery targeted interior gaps; its
success does not establish coverage of every boundary-only gap. No raw download
or lifecycle explanation is inferred from this check.

Next priority: inventory active-trade/missing-mark boundary keys in2021–2022,
then recover verifiable observations through a versioned overlay. Do not relax
the mark gate or forward-fill to improve coverage. Separately define and audit
the early/development identity bridge. These steps precede model performance.
