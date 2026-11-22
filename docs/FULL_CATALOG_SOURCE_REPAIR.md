# Full-catalog source verification and repair — Experiment 018

Registered in [Experiment 018](../experiments/018_full_catalog_source_repair.md)
before implementation and the official-source batch. No model fitting or PnL.

## Completed verification

All 1,577 input-review intervals are accounted for, including all 742 pending
intervals from Experiment017. They produced 788 deduplicated bounded source jobs:
616 funding,151 mark,21 trade. The initial pass made677 HTTP requests (676 HTTP200,
one HTTP400 followed by archive fallback);115jobs reused verified older daily
archive caches. A second pass verified all788checkpoints/source bodies/baselines
with **zero additional requests**. No source request remained failed.

| Result | Count | Interpretation |
| --- | ---: | --- |
| New mark-price observations | 23,492 | Official-source rows saved and deduplicated |
| New funding observations | 1,759 | Observed rates/timestamps; missing interval metadata remains explicit |
| Mark review intervals with all required keys recovered | 122 | Source-level closure; not integrated execution certification |
| Expected initial listing warmups | 831 | Do not invent pre-listing observations |
| Known partial-event flow warmups | 9 | Preserve nonfull-day/history rules |
| Known effective stops | 4 | Preserve settlement handling |
| Funding cases with gap/invalid/freshness failures | 492 | Still fail the registered input checks after official verification |
| Funding cases with reported-duration-only failures | 101 | Rule/interval interpretation review, not proof of missing observations |
| Funding cases with new rates but unverified intervals | 4 | AERGO,BNX,ICP,TLM; do not fabricate duration labels |
| Other required-key gaps | 11 | Four flow intervals and seven final-day close intervals |
| Phase transitions with official terms found | 2 | PUMP,LIT; announcement terms are not observed completion timestamps |
| Conflicting source interval quarantined | 1 | UNFI trade-volume discrepancy |

These dispositions sum to1,577. There are3,917remaining required-key rows:
3,868daily feature cutoffs with incomplete funding checks,42trade-hour keys and
seven final-day close keys. **This is not3,917missing funding payments.** Cases,
cutoffs,observations and underlying events have different units.

## Concrete findings

-380funding-review intervals start2026-06-24. The local/archive and requested
  official REST series omit observations around the same date for many symbols;
  repeated downloads cannot justify filling the omitted rates with zero.
-101funding intervals have only the168hour reported-duration requirement failure,
  without the current gap/invalid/freshness flags. Funding-frequency changes and
  duration-field semantics need a separately recorded correction review before
  changing Experiment017. No threshold was relaxed after seeing these counts.
-REST returned old rates missing from consumed sources:849ICP,648TLM,256BNX,
  sixAERGOobservations. These values are saved; their unestablished interval
  labels block automatic inclusion in the registered-duration feature calculation.
-All122mark review intervals have their required daily23:00UTC hour keys in the
  verified source union. Long gaps include Unicode-symbol periods with no consumed
  monthly mark file. Recovered observations are additive and source-bound.
-UNFIUSDT at2023-11-30 12:00UTC:monthly/canonical and independently downloaded,
  checksum-verified daily archive report total base volume41538,while taker-buy
  base volume is51617.3. REST reports total volume122711.7. The archive violates
  buy-volume<=total-volume; no source was silently selected as a replacement.
-Official[PUMP transition announcement](https://www.binance.com/kk-KZ/support/announcement/detail/e220b78bdf4848e3a61eb9fce99e2580)
  schedules2025-07-14 17:20UTC with up to one hour transition;
  [LIT announcement](https://www.binance.com/en/support/announcement/detail/96ac152ced224d7a92a10a11335f5212)
  schedules2026-01-15 15:15UTC with up to three hours. Actual completion remains
  distinct from the announced schedule; the old open-ended policy was not silently changed.

## Product scope:924identifiers are not924crypto assets

A saved official[exchangeInfo](https://fapi.binance.com/fapi/v1/exchangeInfo)snapshot
matches895of924catalog identifiers. Current types:655COIN,198EQUITY,15HK_EQUITY,
8KR_EQUITY,8COMMODITY,5PREMARKET,3INDEX,2CN_EQUITY,1FX;29are absent from the
current response. All924remain in the scope ledger. Absence today never deletes
historical instruments. Current classification/onboardDate is not certified historical
publication evidence and must not be applied backwards across a reused identifier.

Among775ever-provisional identifiers,the current types include640COIN,96EQUITY,
23absent,8COMMODITY,3INDEX,3KR_EQUITY,2PREMARKET. This does **not** mean their
entire history has that class:MDT,for example,has different historical underlyings.
The775figure must not be advertised as775certified crypto assets. Dated product
and identity scope is required for the corrected backtest.

## Artifacts and reproduction

Ignored repair root:`data/repairs/full_universe/9d8e79788ba25d039b37/`.

- `plan.json`:all1,577case definitions,788jobs,source hashes and code binding.
- `jobs/*/result.json`:per-job results,raw-source references,conflicts and checkpoints.
- `deduplicated_observations.jsonl`:25,251unique source-verified added observations.
- `verified_case_dispositions.csv`:exact-key closure for every interval.
- `remaining_required_keys.csv`:dated remaining checks with explicit units.
- `assessment.json`:final counts and hashes;all_cases_accounted=true,execution_ready=false.
- `phase_evidence.json`, `current_product_scope.csv`, `product_scope_summary.json`:
  official evidence and all-identifier scope review.
- `evidence/UNFIUSDT/conflict_evidence.json`:invalid archive row and source reference.

```bash
conda activate funding-strategy
python -m crypto_factor_research repair-run --repair-dir data/repairs/full_universe/9d8e79788ba25d039b37
python -m crypto_factor_research repair-evidence --repair-dir data/repairs/full_universe/9d8e79788ba25d039b37
python -m crypto_factor_research repair-scope --repair-dir data/repairs/full_universe/9d8e79788ba25d039b37
python -m crypto_factor_research repair-assess --repair-dir data/repairs/full_universe/9d8e79788ba25d039b37
```

Use repair-plan with the input dataset to generate a newly bound plan if downloader
code or source inputs change. Cached failures retry only with explicit--retry-failed.
Responses,request errors,checksums and retrieval timestamps are retained. A rate-limit
response halts further requests. Concurrent passes are locked out.

All33active tests and package lint pass. Original canonical releases and the old
37-identifier performance are unchanged. **The added observations have not yet been
integrated into a new feature/engine release.** No expanded backtest,paid purchase,
private credential request or push occurred. Execution readiness remains false.

The next correction is not another blind download pass:review duration semantics,
apply dated product/phase scope,integrate accepted overlays,and verify the actual
held/target valuation,fill,funding and terminal keys before running financial cases.
Unresolved public funding omissions and conflicting rows remain named blockers;
this report does not claim an error-free market-data source.
