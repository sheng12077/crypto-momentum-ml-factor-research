# Full-universe project remediation specification

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan; code/data inspection performed inline
- Origin Date: 2026-11-22
- Verification Status: PLAN UNVERIFIED; existing input coverage audited separately
- Version Label: full_universe_remediation_v1
- Evidence: current source, registered protocols, existing daily indices and manifests
- No model fitting, strategy backtest, downloads or external data upload in this segment

## Corrected objective

Build and evaluate a time-varying crypto perpetual long/short strategy using every
identifier in the acquired924-entry catalog as a reviewed input, rather than a
fixed pre2021subset. Every identifier must have a date-specific disposition.
The historical data are all available for research; prior OOSinspection is not a
permission barrier. Reports must state that these dates were inspected and cannot
be relabeled as a new untouched holdout. Neither profitability nor perfection is
guaranteed by this specification; technical correctness and economic evidence are
separate acceptance decisions.

## Confirmed root cause and baseline

The original prototype takes40corroborated early records, removesBCH/KNC/LEND,
asserts37symbols, then later preparers inherit that list. It did not evaluate and
reject the other identifiers. Relevant archived sources:prepare_first_development.py
lines103--107; prepare_validation_2023.py line177; prepare_validation_2024.py line203;
prepare_final_holdout.py lines74--75. Existing tests and cash-ledger replays validated
that subset's implementation, not completion of the full-market research objective.

Current published return tables and resume wording are restricted to that prototype.
They are not evidence for the larger requested universe. Publication/paper/live
promotion is suspended pending the corrected scope and its evidence.

## Actual full-data inventory

- Catalog and files accounted for:924.
- Daily Parquet files verified against existing indices:924.
- Used by old fixed prototype:37.
- Never considered by that fixed-cohort gate:887.
- Ever passed the old price/funding diagnostic:787.
- Such diagnostic candidates outside the old pool:750.
- Positive activity in this release:922identifiers.

GAIBUSDT/LENDUSDT have no positive activity in the2021--Oct2026daily release.
That does not prove they never traded outside this window. Existing diagnostic
flags do not certify new feature, execution, lifecycle or point-in-time eligibility.
The audit's new_dynamic_universe_built=false is intentional and must stay visible.

Local artifacts (ignored, not committed):reports/tables/universe_audit/assets.csv,
daily_diagnostic_counts.csv and summary.json. Every catalog entry appears in the
ledger, including corrupt inputs. Flags are counted on observed positive-activity
days to avoid treating every prelisting calendar day as a trading-data failure.

## Mandatory deliverables and completion tests

| Work package | Required deliverable | Acceptance condition |
| --- | --- | --- |
| A. Complete inventory | All identifiers, episode evidence, observed coverage, source hashes and explicit pending actions | Exactly924catalog IDs accounted; no silent drops; missing/corrupt inputs retain rows |
| B. Dynamic universe | Per decision timestamp:eligible/reasons, instrument and identity episode, feature history segment, data availability | New listings can enter after warmup; old delisted contracts retained historically; no fixed37/top-N population gate |
| C. Input/feature panel | Versioned full-universe prices, funding, imbalance and trailing features | Feature values depend only on data available then; no Size/vendor mapping prerequisite for the current3groups |
| D. Execution readiness | Complete required-price/Funding/terminal issue queue before long simulations | All candidate execution checks reported together; future-price availability never used as a past selection filter |
| E. Research experiment | Registered full-universe baseline/ML/random comparisons and cost cases | Same universe/clock/risk/costs per comparison; every planned run recorded; no retrospective threshold revisions |
| F. Architecture consolidation | One package/configuration scheme, one CLI, stable artifact lifecycle | No active import of archived research; no duplicated active implementations; README-only edits cannot invalidate financial replay |
| G. Reports/publication | Coverage, reasons, all runs, net returns, costs, drawdowns, exposure, concentration and constraints | Every result identifies universe/run/data/assumption scope; no unsupported market/alpha/live-readiness claim |

## B. Eligibility rules: reviewed population, not a blanket blacklist

1. Keep all924IDs in the catalog, including aliases, nontrading periods and known
   derivative classes. Proven out-of-scope product intervals get a named scope
   reason; missing review evidence remains a pending item, never 'garbage'.
2. Separate instrument_id, underlying identity episode_id and contiguous valid
   feature_segment_id. A data gap does not automatically create a different financial
   instrument or close a position. Known underlying replacement/conversion resets
   factor history; do not splice unrelated PUMP/LIT/MDTepisodes.
3. First/last archive observation is not proof of official listing/delisting or of
   an announcement's publication time. Record what is observed and what is proven.
4. Include an instrument at each decision once the relevant past inputs mature.
   Twenty/sixty/120day features need their real endpoints/history. Do not fill missing
   momentum/funding with zero just to increase the headline count.
5. Check each datum where it is actually required:factor inputs, sizing, Funding,
   valuation and fills have different requirements. Missing irrelevant intraday mark
   bars must not cause a blanket whole-asset exclusion. Repair relevant gaps.
6. CoinGecko/CMCidentity and historical Sizepublication proof are not requirements
   for the currently selected price/Funding/flow model. Size remains a separate future
   experiment, not a hidden reason to gate the three-factor universe.
7. Delisting/relisting, token multipliers, contract type, equities/composites and known
   order stops get interval-specific evidence/reasons. Missing evidence does not
   justify restricting the whole project to early manually reviewed names.
8. No survival-to-end filter, full-period volume ranking or future-known terminal
   availability filter. Liquidity/capacity rules, if used, are based on then-known
   inputs, preregistered and reported as portfolio constraints, not data absence.

## C--E. Research and execution sequence

- Preserve old37results only as a restricted-universe reference. First change universe
  scope while holding the agreed feature/model/portfolio definitions fixed, so the
  effect of broader coverage is identifiable.
- Default comparison retains five momentum20/60/120,funding7,
  imbalance7 inputs, annual expanding fits, two-week rebalance, EQ5long/5short and
  minimum20available candidates. All models are refitted from the new chronological
  panel; old37trained caches are not passed off as full-universe models.
- Required matched controls:60day momentum, an explicitly defined equal-factor score,
  and random ranking with20fixed seeds registered before execution. Report the entire
  random distribution; do not choose its best or worst path. Twenty seeds do not
  provide high-resolution significance evidence; document sampling limitations.
- Keep costs and data clock identical across compared portfolios. Report5/10/20bps
  adverse slippage scenarios with verified/explicitly assumed fee policy and observed
  funding intervals. No order book means these are scenarios, not measured live impact.
- Verify sizing, lot/tick/min-notional, margin and order rejection behavior for the
  instrument population. When historical exchange filters are unavailable, label that
  limitation and distinguish historical proxy research from present-day feasibility.
  Include a separate5000USDT feasibility case if assessing the user's small account;
  do not optimize strategy rules for the best starting capital.
- Preflight all924instrument constructions and all potentially needed rebalance
  proxies before costly runs. Source downloads have explicit queues/budgets/retries,
  reuse verified caches and never loop indefinitely or mutate raw originals.
- Unknown held terminal settlement is an explicit issue, not a fabricated cashflow,
  asset deletion or ignored loss. Retrieve verifiable settlement/index evidence where
  available. If unavailable, separately registered proxy/bounded sensitivity scenarios
  must be labeled approximate; do not certify an exact primary path without evidence.
- Report that seven-day labels and two-week holdings differ. After the universe-only
  comparison, allow a separately registered7versusnext-rebalance-horizon label ablation.
  Buffer, weights and extra factors are not mixed into this first scope repair.
- Annual SHAP, per-factor ablations, rank/return diagnostics and month/asset/side
  attribution accompany performance. SHAP explains model predictions, not causal PnL.
- All seen years can be used for debugging/model research. Record trial/config IDs and
  research usage instead of claiming a newly untouched historical OOS. Future paper
  data would be new evidence if that separate stage is later justified.

## F. Target structure and naming

A single canonical package name (proposed crypto_factor_research),lower_snake_case
modules/functions,one named configuration schema and one CLI. Existing remote slug
is a user-owned URL, not an extra implementation namespace. No remote rename here.
Start with flat modules; split directories only when responsibilities actually grow:

```text
src/crypto_factor_research/
    config.py           # explicit validated settings, no magic global ROOT switches
    data.py             # source/availability schemas and verified readers
    universe.py         # catalog, identity episodes and dated eligibility
    features.py         # factor arithmetic and known-time checks
    models.py           # training, labels, forecasting, SHAP
    portfolio.py        # deterministic ranking, constraints, targets
    simulation.py       # Nautilus events, execution, Funding and ledgers
    evaluation.py       # matched metrics, comparisons and attribution
    reporting.py        # figures/tables only
    cli.py              # one supported entry point
configs/                # semantic experiment configs; no date-named implementation files
experiments/            # registrations and concluded result summaries
```

Module count is not an equality target. Thin wrappers, complete source-tree copies
and splitting a function into several modules do not count as consolidation.
Do not rename or move the entire tree again before inventorying dependencies and
user edits. Preserve the existing Git baseline and byte-exact external backups;
resolve historical source from its recorded revision when needed, rather than keep
multiple complete active source trees on disk. Do not delete old data/caches or
rewrite Git history. Historical results remain traceable to the old implementation.

The target layout/interface is a specification, not already implemented software.

## Artifact lifecycle and reproducibility

```text
data/raw/               # immutable source bytes and retrieval metadata
data/canonical/         # normalized observations with provenance/episodes
data/features/          # data/config-keyed feature cache
artifacts/models/       # model cache plus training/label/cutoff metadata
runs/<run_id>/          # manifest,logs,orders,fills,funding,nav,metrics
reports/<run_id>/       # derived presentation of an existing run
tmp/                    # disposable scratch only; never authoritative research state
```

Existing shared raw/canonical storage is reused; no duplicate market-data download.
Long-lived models/results leave interim through a mapped migration, not destructive
cleanup. Cache/run identity depends on actual input data, financial configuration,
model/training and relevant simulation/selection code. Record source revision too.
Report/badge/READMEchanges get report provenance and do not force a new simulation.
Output directory names and cosmetic text are not financial inputs. Every run records
status/planned/completed/blocked cases; a completed report is not all-case success.

One small end-to-end synthetic contract must work on a fresh clone with no market
data. Full-data commands state exactly which local artifacts are prerequisites.
Test the committed tree in isolation so user working edits cannot hide missing code.

## Implementation order and stop conditions

1. Deliver this specification and complete source-bound924row audit (this segment).
2. Register the full-universe experiment expectation/thresholds on main before its
   implementation or performance inspection. Then implement dated universe/feature
   inputs in a research branch, with all924dispositions and a complete gap queue.
3. Resolve required execution/terminal assumptions explicitly; build representative
   synthetic new-listing/delisting/reused-symbol cases and a bounded real data pilot.
4. Run the registered whole-data controls/models and persist every attempted result.
   Long jobs are handed off only after full preflight plus small-scale validation,
   with exact command, log, output and success/failure summary. No surprise retry loop.
5. Consolidate and migrate one responsibility at a time, validating unchanged outputs
   where semantics are unchanged. Produce final scientific/engineering reports.
6. Update public README/resume only after scope and remaining limits match actual
   artifacts. No automatic push, deployment, live trading or paid data purchase.

A failed research hypothesis is a reportable outcome. Missing assets, unexplained
filters, hidden errors or mislabeled performance are failures of project completion.
No claim of broad-market profitability is accepted just because unit tests pass.
