# Publication readiness and scope -- 2026-11-22

The release publishes a completed research finding and reproducible implementation,
with explicit limitations. It does not certify a profitable live strategy or claim
that every case in the original final-holdout protocol completed successfully.

## What belongs on main

- The packaged continuous ML workflow, synthetic example and installation instructions.
- Verified full-period reconstruction and separately identified original OOS results.
- Source-preserving historical archive, preregistrations, tests and research notes.
- Aggregate Markdown results and selected README figures. No market observations,
  trained model binaries, financial CSV/Parquet files, private credentials or logs.

The original final-holdout plan had12cases:8financial cases completed and4momentum60
control cases remain blocked by unverified EOSterminal settlement. Its recorded
success/data_complete flags remain false. ML cases and their replays are verified;
blocked matched-control gates remain unavailable. Publication closes this work as
a report of supported ML evidence and a documented limitation; it does not alter
registered thresholds, invent settlement, or advertise the whole protocol as passed.
Any future attempt to resolve that control is separate research work.

## Supported performance claims

- Full retrospective2022--Oct2026: return+84.06%,Sharpe.645,MDD-26.77%.
- Original independent2025--Oct2026OOSaccount: return+16.31%,Sharpe.435,MDD-24.79%.
- Same-date slice of the full account:+24.08%; it inherits prior holdings and is not
  substituted for original OOS. All OOSdates are now disclosed, not reusable fresh OOS.
- Conditional37-identifier cohort and historical publication-vintage limits remain.
  No paper/live readiness, market-beta-adjusted alpha, or reliable future profit claim.

## Checks on the committed candidate

The code tree at1e99966 was exported with git archive into an ignored isolated
snapshot, without local market-data aliases or uncommitted edits. That snapshot
passed356tests and31subtests. Release-preparation changes after that snapshot are
Markdown only. Test log stays local at reports/acquisition/
publication_committed_tree_tests_20261122.log.

A scan of483reachable text-sized Git blobs found no matches for the checked common
credential patterns. Reachable history contained no data/ paths or market CSV,
Parquet,ZIP or database archive paths. This is a limited automated check, not a
universal guarantee about every possible secret representation.

Three actual package003case replays match the original financial hashes exactly.
The later badge-publication change affects only reporting/publication.py and the
package output namespace; financial data/model/engine sources and runtime match
that verified version. Package004is reserved for a future source-bound replay;
no old contract or output was overwritten to make publication checks pass.

Existing unrelated working edits remain outside the release commit. They are
backed up locally before branch switching and restored byte-for-byte afterwards.
The public tree is tested from committed content rather than those local edits.

## Publication operation

Local main must contain this release and show the new README before pushing.
Do not force-push, amend old commits or change registered thresholds. GitHub remote:
https://github.com/sheng12077/crypto-momentum-ml-factor-research.git

The latest remote read requested GitHub authentication; successful access must be
rechecked after sign-in. The user elected to push main personally; the assistant performs no push or login
flow. The local main research merge is9a9b4c7, followed only by handoff documentation.
No credentials should be entered into repository files or chat messages. No push
has been performed by this release-preparation task.
