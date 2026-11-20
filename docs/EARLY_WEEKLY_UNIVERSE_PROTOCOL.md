# BTC evidence integration and 2020 weekly coverage

Registered before implementation/execution on2026-11-20. Baseline main8d68fa0,
identityv007 has81records/39corroborated/37of40history candidates;BTC public audit
v20261120_002 passed7checks using96trade+96mark hourlybars and12fundingevents.

## Scope and expectation

Create a new immutable identity release consuming the BTC audit,and a descriptive
weekly coverage audit of the same81early identifiers during2020. Expect onlyBTC
to change identity state,resulting in40corroborated identities overall and38of40
ever-history candidates. This is not a full924-ID or2021–2026universe audit.
No market-data downloads,Size joins,performance,model fitting,orOOS inspection.

## Fixed acceptance gates

- Bind hashes of v007 reports/runbinding,public audit reports/reviewbinding,
  public audit configuration/tool/dependencies,raw response metadata and source
  bodies,and early panel manifest/index/daily files. Reject changed inputs.
- Recompute the seven pure publicAPI/archive comparisons from saved bodies and
  the dated2019notice gate;require exact agreement with the saved audit checks.
  Require current metadata/archived sample identity,prior numeric/name/history
  proofs and scope to match the previous BTC rule. Never consume a summary flag
  alone. Current metadata is retrospective,not historical trading permissions.
- Replace exactlyBTC's old failed document-only venue gate with the explicitly
  documented combined retrospective evidence basis. Preserve the exact old rule
  and fingerprint as superseded. Preserve all other80records verbatim. Scope,
  USD scale,no-splice,and every unproven lifecycle/publication/cashflow/strict
  eligibility flag stay unchanged. BAND/SXP remain pending;do not force approval.
- Reuse the frozen weekly calendar:52Mondays2020-01-06through2020-12-28,00UTC.
  Each observation is the previous UTC day's existing daily input,not a newly
  assumed executable fill. All81IDs are evaluated at every decision time.
- Report separate counts:existing price_history_diagnostic_candidate;that flag
  intersected with corroborated identity,decision time within[start,end),valid
  close,complete trade day,not composite and not known settled;then the latter
  intersected with existing funding_freshness_diagnostic. Do not rename these
  sets strict tradability or proven paid funding. Do not silently forward-fill.
- Export81identity records,4212asset-week diagnostic rows,52weekly counts and
  member lists. Keep overlapping diagnostic reasons and a deterministic primary
  reason distinct. Reconcile every count with its underlying membership.
- Descriptive statistics include all52weeks(including warm-up zeroes),first
  nonempty week,min/median/max,and counts meeting fixed20/30-name thresholds.
  These thresholds describe coverage only;they do not select a strategy.

## Validation and stopping point

Test exact scope boundaries,stale/missing funding,settlement/index exclusion,
immutability of all prior approvals,failed/tampered audit rejection,and count
reconciliation. Run this small offline audit locally and verify same-version
replay/report hashes. Old identity,API audit and canonical releases stay intact.
Stop with the updated identity evidence and weekly coverage findings;do not
automatically extend dates,apply Size lags,change strategy/OOS splits,or launch
a backtest. Next work should follow the observed coverage and open limitations.

## Completed release

Offlinev20261120_001 completed6.031s;replay4.672s,zeroHTTP. All seven derived
report hashes identical. Full234tests passed(7new);changed-file Ruff passes.
BTC audit's7checks recomputed from raw public responses/archives;other80identity
records unchanged. BTC old rule retained as superseded with unchanged scope and
all limitations. New identity release:81records,40corroborated overall,38of40
ever-history candidates;BAND/SXP remain pending. LEND/AAVE have no qualifying
2020history window;UNI remains registered-pending without qualifying history.

New current identity source:
data/interim/early_weekly_universe/v20261120_001/asset_review.json.
Do not keep using the preserved v007/37-of40 report as the latest release.

| DecisionUTC | Raw history count | Identity/scope/history count | Also fresh observed funding |
|---|---:|---:|---:|
| 2020-01-06 |0|0|0|
| 2020-05-04 |3|3|3|
| 2020-07-06 |24|24|24|
| 2020-10-05 |25|25|25|
| 2020-12-28 |40|37|37|

Across all52weeks(including17zero weeks),identity/scope/history count is
min0/median24/max37;35nonempty weeks,29weeks>=20names,9weeks>=30names.
First nonempty weekMay4;first37-name weekDecember21. Counts are calendar-specific,
not a fixed38-asset portfolio. Raw862asset-weeks reduce to844:5BAND+6SXPpending
identity weeks and7BCHweeks beyond its verified fork cutoff. In these844weeks,
the existing observed-funding freshness flag removes no additional rows. This
does not establish paid funding or freshness outside this sampled weekly subset.

Outputs:81identity JSON/CSV rows,4212asset-week CSV rows,52weekly JSON/CSV rows,
missing evidence and btc_evidence_consumption.json. Every membership/count and
primary reason reconciles. Overlapping reasons are kept separately. All old
inputs/identity/API/canonical releases retained;no Size join/PnL/OOS generated.
Log reports/acquisition/early_weekly_universe_v20261120_001.log. User rerun not
needed;optional verified summary command:

```bash
python scripts/build_early_weekly_universe.py summary --version v20261120_001
```

This is2020/81-ID diagnostic coverage only,not the924-ID or2021–2026universe,
nor full trading eligibility. Next task should address research-input continuity,
Size availability assumptions and execution/funding semantics before backtesting;
do not extend these identity scopes or claim later-period coverage automatically.
