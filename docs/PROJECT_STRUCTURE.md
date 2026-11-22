# Project structure and frozen-source migration

## Supported workflow

The active implementation is the `momentum_data` package under `src/`. It has no
imports of the archived research scripts. Public commands are `smoke`, `verify`,
`replay`, `summary`, and `publish`, available as `python -m momentum_data` or the
installed `momentum-research` command. The three files in `scripts/` are small
launchers: they do not contain factor, model or accounting logic.

- `data/historical.py`: hourly data, terminal boundaries and event calendar.
- `data/benchmarks.py`: timestamp normalization and fixed-unit spot benchmarks.
- `data/preflight.py`: complete held-price/forecast/schedule verification.
- `features/factors.py`: frozen past-only features and episode history arithmetic.
- `models/annual.py`: matured labels and existing annual model/prediction/SHAP caches.
- `portfolio/ranking.py`: deterministic cross-sectional ranking and schedule.
- `backtest/engine.py`: quantities, fills, fees, Funding and terminal guards.
- `backtest/workflow.py`: separate package replay and independent every-fill/Funding audit.
- `reporting/analysis.py`: metrics and plotting; `reporting/publication.py`: public results.
- `integrity.py`: immutable artifacts, preserved-source resolution and package contracts.
- `settings.py`: the named run in `config/continuous.json`; `paths.py`: local root overrides.

The original public `momentum_data.reader` and `backtest_analysis` modules remain
for backwards compatibility. Tests compare relevant public metrics to the original
sources; no historical strategy decision, fee assumption or annual model is changed.
Only the frozen version is configured: execution fee/lot constants remain frozen
in the instrument adapter. The JSON documents their values; changing it alone is
not a supported new strategy/cost experiment and must not be advertised as one.

## Historical research

`research/legacy/` preserves the earlier layout of scripts, config, tests, notebooks,
source, docs and protocol copies. Source bytes remain unchanged, so the original
contracts can still verify historical claims. Root `experiments/` remains the public
preregistration record. Older acquisition and fitting tools are archived evidence;
they are not imported by the current execution/package workflow.

Local-only `research/legacy/data` and `reports` aliases point to the existing ignored
working folders. They are ignored and never committed. This compatibility layout
supports local historical checks without duplicating market data. A fresh clone
should run the public synthetic tests first; historical data-dependent commands
still require the original local caches. To create these optional aliases on WSL:

```bash
ln -s ../../data research/legacy/data
ln -s ../../reports research/legacy/reports
```

Create an alias only if that path is absent; never replace an existing directory.
Historical tests can be run explicitly with `python -m pytest research/legacy/tests -q`.
The current default tests are in root `tests/`. Notebook outputs and pre-existing
uncommitted edits are preserved at their archived paths, not silently staged.
Historical docs use links within their preserved layout; the root README archive
links point into it. Old commands in those docs are historical and require the old
layout/caches; current run instructions are in the root README.

## Preservation checks

The original continuous output stays in `data/interim/continuous_reconstruction/`.
Its contracts are not deleted or rewritten. `verify_frozen_contract` resolves each
original logical `scripts/`, `src/`, and `experiments/` entry against the archived
source copy; data entries resolve against the configured local data root. It checks
the original runtime too. Saved report and case hashes are rechecked independently.

The new engine writes separate cases under `data/interim/continuous_package/`.
Its source/configuration has its own immutable contract. The two cost cases and
primary replay must match their original financial SHA256 values exactly, in
addition to the independent source-VWAP/fee/pre-fill Funding audit. A mismatch
fails rather than relabeling existing results as newly reproduced.

No raw data, model binaries, API keys, logs, or result CSV/Parquet files are shipped.
The tracked monthly heatmap and Markdown tables contain summarized research results.
The project has no configured Git remote and this migration does not publish it.

## Completed verification

The reorganized engine actually replayed all three cases and matched the original
financial hashes exactly. Combined current/historical tests:354passed,31subtests.
See [migration verification](PACKAGE_MIGRATION_VERIFICATION.md) for source equality,
independent ledger audits, notebook execution and environment-check limits.
