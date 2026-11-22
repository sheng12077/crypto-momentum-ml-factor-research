# Package migration verification

This is an engineering refactor, not a new strategy or economic experiment. The
original protocol016 outputs and contracts remain intact. No model fit or download
was performed. Frozen source bytes are preserved under research/legacy; current
implementation imports only the package and its third-party dependencies.

## Completed checks

- Editable install succeeded using the existing funding-strategy environment.
- Public CLI help and synthetic accounting example run from outside the repository.
- 7 current tests and 347 archived tests passed separately, then all 354 tests and
  31 subtests passed together in one process (18.57 seconds).
- Ruff undefined-name/error checks and compilation passed for active source/launchers.
- Whole-data preflight:5annual caches,127rebalance dates,243851events; unchanged plan.
- Actual new-engine runs:5bps,10bps,and independent5bps replay. Each matches its
  original frozen financial SHA256 exactly; independent fill/fee/Funding audits pass.
- All current English notebook code cells executed successfully on saved results;
  executed output remains ignored under reports/acquisition.
- Public Markdown links resolve. Git index/history contain no data/market archive
  paths; a limited credential-pattern scan found no matches. This is not a promise
  that a pattern scan replaces a future publication review.

## Financial equality

| Package case | Financial SHA256 (equal to original) | Fills audited | Funding rows audited |
| --- | --- | --- | --- |
| slippage_5bps | `6b11fd1badf6c5324f3e3609f216a1973fea35ecb1d564a7bc5fc8764a490879` | 2075 | 54370 |
| slippage_10bps | `df5e6936d6a6ab957509d28a7a499320dc20b0fcac6334284f5c99402bfa10db` | 2075 | 54370 |
| primary_replay | `6b11fd1badf6c5324f3e3609f216a1973fea35ecb1d564a7bc5fc8764a490879` | 2075 | 54370 |

Each case also reconciles daily cash/unrealized NAV and final account ledger. The
original ending NAV and all performance claims are unchanged by the reorganization.
The local migration manifest is data/interim/continuous_package/v20261122_002/
verification.json; input and source/configuration contracts are retained beside it.

## Scope and remaining limits

No GitHub repository was created and nothing was pushed. Market data, trained models,
financial CSV/Parquet files, local aliases and logs remain ignored. Existing unrelated
uncommitted modifications moved with their historical files; original index blobs
were checked for all19original status paths and those edits were not staged.
The current package replays cached annual models; acquisition/training from raw data
remains in the archive and requires its historical inputs. Environment installation
was tested with existing dependencies; a network install into a brand-new environment
was not performed. The top-level runtime pins are not a complete transitive lock.

See [architecture](PROJECT_STRUCTURE.md), [README](../README.md) and
[research results](CONTINUOUS_RECONSTRUCTION_RESULTS.md) for supported commands,
results and unresolved economic/data assumptions.
