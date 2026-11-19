# One-command processing of all81 early identifiers

Registered on main at `544965e`;implementation branch:
`infra/unified-early-identity`. Scope is the81 early contracts,not the924-ID ledger.

## Command

In the momentum_strategy directory on WSL:

```bash
conda activate funding-strategy
python scripts/run_early_identity.py run --fetch
python scripts/run_early_identity.py summary
```

The first command processes the entire list;there is no eight-case limit.
`--fetch` permits only additional source URLs explicitly registered in the plan.
The current plan has no additional sources,so this command makeszero HTTP requests.
It verifies existing evidence and recomputes results;it does not invent missing
official announcements. Processing all81 is different from approving all81.
No user rerun is needed after the completed validation below.

The pilot flag `--pilot` exports the eight registered boundary cases. Common
historical/panel evidence is still validated in full;it is not a partial data audit.
Runtime of the initial native full run was41.063s;allow roughlyone minute on this
workspace,depending on filesystem speed. Large future source additions take longer.

## What the script does

1. Verify54 historical CMC raw/parsed snapshots and81 daily panels once;reproduce
   the original inventory queue. It does not recursively invoke previous runners.
2. Verify previous config,code,dependencies,source bodies,capture failures and
   panel bindings;recompute all24 batch decisions with frozen pure helpers and
   compare them with the saved decisions. Reproduce the four base/supplement
   decisions,check predecessor artifact hashes and recheck primary IOTA evidence.
3. Apply any registered additional source/case assertions through the same engine.
   New URLs are deduplicated;existing captures reused;old failed URLs not retried.
   Transport/5xx retries bounded;authorization/rate denial stops acquisition.
   Terminal failures,metadata and bodies are verified on resume.
4. Export all81 records,independent identity/history states,a missing-evidence
   queue and a CSV. Keep QTUM funding and IOST support-only limitations. Composite
   DEFI is retained but not mapped to a standalone token Size. No automatic joins.

The distinction between identity and history matters:LEND/AAVE have supported
identity rules but no qualified120-day2020price window. A unique ticker lead is
not an approval;no qualified price-history week is not permanent exclusion.

## Outputs and success criteria

Default ignored root:`data/interim/early_identity_all/v20261119_003/full/`:

- `asset_review.json`:all81 rows,rule details,fingerprints and provenance.
- `asset_review.csv`:compact human-readable status table.
- `missing_evidence.json`:specific missing assertions or failed proof gates.
- `evidence_checks.json`:recomputed per-case checks.
- `additional_sources.json`:new-source outcomes(currently empty).
- `run_config.json`,`summary.json`:input/code/source bindings and report hashes.

Log:`reports/acquisition/early_identity_all_v20261119_003.log`.
`summary` verifies exported report hashes before printing. JSON writes and CSV
replacement are atomic. Relative binding paths use POSIX form for Windows/WSL
consistency. Use one writer/host at a time;Windows and WSL locks are not shared.

Expected full baseline:processing success=true,full_scope=true,81 rows,862
candidate asset-weeks,one common validation pass,zero old-runner invocations,
zero HTTP. Identity counts:24corroborated,4registered/pending,52missing assertions,
1composite index. Of40 identifiers with qualified2020price-history weeks,22 have
corroborated identities. The other18 include3registered/pending and15unconfigured.

`all_identity_checks_complete=false` remains intentional:the outstanding research
has not been completed by wrapping it in a script. Historical Size publication/
vintage,execution,specifications,cashflows and strict eligibility remainunproven.
No canonical data,factors,labels,models,PnL or OOS performance were generated.

## Extend the plan without another batch script

The registry is `config/early_identity_all_20261119.json`. Add new source specs
and asset assertions under `additional_plan.sources` and `additional_plan.assets`.
Source entries use `id` and either `url` or Binance `article_code`;each asset
references its provider,name and futures sources,expected numericID/name/symbol,
nonempty name/futures evidence terms,and explicit2020UTC scope. Declare native
asset status or an exact Ethereum address plus its official source. Empty templates
cannot pass. The existing batch3 plan shows token/migration assertion fields.

New project domains must be explicitly registered in `allowed_hosts`. Never put
API keys or credentials in the plan. The additional downloader has a32MiB ceiling.
The script does not search for announcements or certify the economic meaning of
human-written assertions;those sources and assertions must be reviewed first.

Register new assumptions/source assertions before executing them,following the
repository workflow. Changed plans/code need a new output version:

```bash
python scripts/run_early_identity.py run --fetch --version v20261119_004
```

A conflicting case is rejected unless the new assertion explicitly supplies
`replaces_rule_sha256` matching the existing record and a `replacement_reason`.
The superseded rule remains in provenance. A changed rule never silently replaces
old evidence or approval thresholds. Earlier failed capture URLs remainfrozen;
obtain different primary evidence through a separately registered follow-up.

## Validation versions

The initial v001 eight-case pilot passed40.938s/zeroHTTP. v002 full baseline
passed41.063s/81rows/zeroHTTP. These engineering checkpoints are retained.
Final v003 includes portable paths,atomic CSV/report-hash verification and
validation that incomplete additional-case templates cannot approve an identity.
Full v003 completed39.234s/81rows/zeroHTTP.208tests pass(11new);changed-file Ruff
lint/format pass. The JSON/CSV counts and unique identifiers reconcile to81;all
strict-eligibility flags stayfalse. Same-version replay and report hashes were
checked. Engineering checkpoints v001/v002 remainintact;no old batch output was
rewritten. The final result is also recorded in `docs/PROJECT_STATUS.md`.
