# Current follow-up: v007

2026-11-20 update:separate BTC public audit v20261120_002 passed7of7checks,
96trade+96mark hourlybars and12fundingevents. Combined BTC identity evidence
satisfied;see BTC_PUBLIC_API_PROTOCOL.md. It writes a sidecar only;v007's37of40
count is unchanged until explicit consumption in a new release. No OOS/PnL.

Nine-case follow-up registered5440693;see EARLY_IDENTITY_NINE_FOLLOWUP.md.
Default plan config/early_identity_remaining_004_20261119.json,18additional
cases/60sources. Hash-verified v006 evidence inherited;8newURLs only. Existing
passed rules must reproduce exactly;terminal failures never retried. Scope81IDs.

```bash
python scripts/run_early_identity.py summary --version v20261119_007
```

Summary verifies report hashes. Output data/interim/early_identity_all/v20261119_007/full/;
log reports/acquisition/early_identity_all_v20261119_007.log. A same-version
run --fetch replays cached evidence;changed plans/code require a new version.
No eligibility guarantee,canonical joins,models,PnL,orOOS access.
Completed fullv007:37of40history candidates supported(up from31),39corroborated
overall. Newly passed BCH/ZRX/COMP/RLC/SNX/WAVES;all33previous passes unchanged.
Remaining BTC(ResearchHTTP202),BAND(futures proof),SXP(legacy address/label).
Full219tests passed. This acquisition is already complete;no user rerun needed.

# Preserved v006 command and validation

Remaining-case protocol registered on main at4de60fe, before implementation
and acquisition: REMAINING_EARLY_IDENTITY_PROTOCOL.md. Scope remains the81
early contracts, not the924-ID ledger.

In the WSL momentum_strategy directory:

```bash
conda activate funding-strategy
python scripts/run_early_identity.py run --fetch --version v20261119_006
python scripts/run_early_identity.py summary --version v20261119_006
```

The default is now config/early_identity_remaining_003_20261119.json:18 additional
cases,59 explicit public URLs. Existing successful captures are reused by URL;
failed captures remain frozen. Allow approximately3–8minutes for the first full
acquisition, depending on network latency; repeated transport failures may take
longer. Resume using the same command. Use one writer/host at a time.

Small pilot: --pilot selects ALGO/KNC/DOT and prunes other additional cases AND
their source dependencies before HTTP. Shared historical inputs and all frozen
old rules are still verified in full. No recursive batch runners.

Cases:ALGO,ZIL,KNC,ZRX,COMP,OMG,DOGE,SXP,BAND,KAVA,RLC,MKR,SNX,WAVES,DOT,
plus explicitly hashed replacements for BTC/BCH/ETC. Superseded rules remain.
The source plan lists assertions to test, not18 pre-approved mappings.

- KNC: ID1982/legacy address only. Current KNCL alias requires a separate Kyber
  migration assertion; new KNC ID9444 is rejected. Historical symbol stays KNC.
- SXP: historical Swipe ERC20 plus later Solar/migration evidence. Missing old
  Ethereum metadata keeps it pending; no historical native-phase inference.
- DOT: superseding August22 scope, not original August20; separate redenomination
  evidence, no cap scaling or price/history splice.
- BAND: conservative August4 scope from the official monthly report, not an
  exact listing timestamp. Venue native/token phase remains unproven.
- BCH: still ends2020-11-15 12:00 UTC exclusively; no post-fork identity repair.
- ERC20 addresses require independent project sources or direct explorer token
  pages with additional token-name/symbol assertions for OMG/SXP/MKR. Endpoints
  must actually return the required content; a registered URL is not proof.

New ignored output: data/interim/early_identity_all/v20261119_006/full/.
Files:asset_review.json,asset_review.csv,missing_evidence.json,evidence_checks.json,
additional_sources.json,run_config.json,summary.json. Log:
reports/acquisition/early_identity_all_v20261119_006.log. Summary verifies hashes.

Full success means success=true,full_scope=true,identifiers_processed=81,
additional_cases_evaluated=18,additional_sources_selected=59,
common_input_validation_passes=1,old_batch_runners_invoked=0. Compare supported
history identifiers against baseline22; do not assume40. Check source states and
pending gates separately. all_identity_checks_complete may remain false.

No automatic source substitutions or gate weakening. Changed plan/code needs a
new output version. Acquisition uses a32MiB total budget and existing response
limits/pacing/bounded retries;HTTP403/429 pauses subsequent requests. No keys or
purchases. Identity corroboration does not prove Size publication vintage,
contract specifications, historical eligibility, or paid funding. No canonical
joins, labels, fit, PnL, or OOS access. Current identity sources are retrospective
evidence, not historical features. QTUM/IOST limitations remain.

v004 pilot obtained12 sources:ALGO passed;KNC date spelling and DOT ratio
wording failed literal clauses. The preserved source bodies say "20th April 2021"
and "redenominated by a factor of 100". v005 registers those equivalent clauses
and more explicit migration
wording;no date,ratio,scope,address,ID,or acceptance requirement is relaxed.
Original v004 plan/proofs remain. Twelve hash-verified captures were copied to
the new cache,with predecessor source-manifest hash recorded in the new plan.

v005 cache-only pilot passed all3 cases in60.156s,zeroHTTP. Final v006 changes
only source order:the three direct explorer endpoints are last,so an explorer
access denial cannot preempt all venue/project checks. Assertions are unchanged;
the verified captures are reused. No denial has been observed in this pilot.
Final v006 pilot:3of3 identity rules passed,23in-scope candidateweeks,46.656s,
zeroHTTP;all five report hashes identical to v005. Final215tests and changed-file
Ruff lint/format checks passed. This is a pilot,not the full18-source-case result.
Separate v006_offline full smoke:81records,18additional cases,59sources,
45.375s,zeroHTTP. All3predecessor replacements accepted;baseline22of40supported
retained. Six old captures reused,53notrequested. This is a processing check;
use v006 for full acquisition,not the deliberately frozen offline version.

## Archived v003 baseline documentation

The sections below describe the completed v003 baseline and its original empty
additional plan. They do not describe the current default. Its old outputs and
config remain intact. Old code-bound versions cannot be rerun with changed code;
their summary hashes can still be verified.

# One-command processing of all81 early identifiers (v003 archive)

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
