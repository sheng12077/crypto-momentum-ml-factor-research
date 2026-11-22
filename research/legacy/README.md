# Historical research archive

This directory preserves the earlier research layout and the exact sources bound
by the existing backtest contracts. It is not the current public package entry point.
Start with the [root README](../../README.md) and [architecture notes](../../docs/PROJECT_STRUCTURE.md).

- `scripts/`: original acquisition, lifecycle review, fitting, experiments and reports.
- `tests/`: historical regression tests; existing local edits remain unstaged.
- `config/`, `experiments/`, `src/`: historical configuration/protocol/source references.
- `docs/`, `notebooks/`: historical methods, reports and saved analysis notebooks.
- [Previous landing page](README.snapshot.md): the original project presentation.

The current `momentum_data` package does not import these scripts. Frozen contract
verification resolves their original logical source paths here. Local ignored
`data` and `reports` aliases provide access to existing working artifacts without
copying or committing them. See the architecture notes before running archived tools.

To run historical tests explicitly from the repository root:

```bash
python -m pytest research/legacy/tests -q
```

Do not edit frozen source merely to bypass a contract mismatch; use a new versioned
workflow and compare it against the preserved financial outputs.
