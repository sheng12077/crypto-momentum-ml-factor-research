# Time-Series Momentum Research

Standalone BTC/ETH medium-frequency, volatility-scaled time-series momentum
and trend-following research.

- `experiments/`: preregistrations and immutable result reports.
- `docs/`: literature, methodology, assumptions, and risk documentation.
- `src/`: strategy implementation and command-line interfaces.
- `tests/`: strategy and accounting regression tests.
- `scripts/`: reusable data and research entry points.

This repository begins a new experiment sequence. Its first strategy experiment
will be Experiment 001 and must be preregistered on `main` before implementation
or performance inspection.

Datasets and generated backtest artifacts are excluded from Git. The local
`data/raw`, `data/canonical`, and `data/catalog` paths link to the shared,
strategy-neutral market-data lake. Momentum-specific features and backtest
outputs belong in ignored `data/interim` and `data/processed` directories.

## Current research notes

- [Momentum and trend-following research landscape](docs/momentum_research_landscape.md)
- [Candidate strategy families before Experiment 001](docs/candidate_strategy_families.md)
- [Project status and handoff](docs/PROJECT_STATUS.md)
- [Historical universe feasibility](docs/historical_universe_feasibility.md)
- [WSL raw-data acquisition commands](docs/USDM_ACQUISITION.md)
