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

Datasets and generated backtest artifacts are excluded from Git. In the local
umbrella workspace, `data` is an ignored symbolic link to `../../data`.
