# Crypto Cross-Sectional Factor Research

A reproducible, medium-frequency crypto long/short research project using annual
LightGBM forecasts and NautilusTrader execution/accounting. Momentum, funding and
aggressive-buy/sell imbalance rank a conditional 37-asset USDT-perpetual cohort.

**Current status: completed retrospective backtest; no live profitability claim.**
The uninterrupted 2022--October 2026 account is net profitable with lower historical
volatility/drawdown than BTC/ETH holding, but monthly consistency is weak and results
are substantially stronger in development years. Paper/live trading is not implemented
or certified by these results.

## Continuous performance

| Series | Total return | CAGR | Sharpe (rf=0) | MDD | Annual vol. | Calmar |
| --- | --- | --- | --- | --- | --- | --- |
| Strategy (5 bps slippage) | +84.06% | +13.45% | 0.645 | -26.77% | +24.13% | 0.503 |
| Strategy (10 bps slippage) | +67.56% | +11.27% | 0.564 | -27.96% | +24.16% | 0.403 |
| BTC spot buy-and-hold | +64.02% | +10.78% | 0.455 | -66.93% | +50.34% | 0.161 |
| ETH spot buy-and-hold | -40.13% | -10.07% | 0.185 | -74.01% | +68.33% | -0.136 |

The account starts with USDT 100,000 on Jan 1 2022. Last valuation is **Oct 31 2026
00:00 UTC**, not the end of that civil day. Positions and capital persist across years;
there is one final liquidation and no yearly cash reset. Spot benchmarks buy once,
hold fixed units and sell once. All periods are already inspected; this reconstruction
is **not a fresh OOS test**. See [full results and limitations](docs/CONTINUOUS_RECONSTRUCTION_RESULTS.md).

## Monthly net returns

![Continuous strategy monthly net returns](docs/assets/continuous_monthly_returns.png)

- Positive months: **28/58 (48.28%)**; median month **-0.11%**.
- Best month: **2022-06, +20.40%**; worst: **2026-10, -20.33%**.
- Return excluding the best month: **+52.87%** (descriptive compounding check).
- From 2024 onward: **+8.09%**, versus **+84.06%** over the full path.

Monthly values compound daily NAV changes grouped by UTC snapshot date, using the
saved report's bucket convention. October 2026 is partial; November/December are
unobserved. Green months do not establish a persistent edge or statistical significance.

| Year | Strategy | BTC spot | ETH spot |
| --- | --- | --- | --- |
| 2022 | +44.31% | -64.53% | -67.89% |
| 2023 | +18.00% | +153.74% | +90.97% |
| 2024 | -13.59% | +120.20% | +46.70% |
| 2025 | +40.58% | -4.64% | -11.55% |
| 2026 (partial) | -11.02% | -13.20% | -24.77% |

2022--2023 informed development; 2024 was frozen validation; 2025--2026 were the
original holdout, now revealed. The continuous reconstruction was registered after
all results were observed. Annual slices include the cross-year daily return and
therefore differ from separately liquidated, fresh-cash annual runs.

## Frozen strategy and simulation

- Five inputs across three groups: 20/60/120-day momentum, seven-day funding,
  seven-day taker-quote imbalance. The momentum horizons are model features,
  not a staged-entry position-control rule. No Size feature or buffer in this version.
- Existing annual expanding-window model caches; strict matured-label cutoffs.
  LightGBM parameters and forecasts are unchanged; annual SHAP is verified.
- Top five long / bottom five short, equal +/-10% target NAV per asset; at least
  20 eligible candidates. Target gross exposure 100%, target net notional zero;
  actual exposures drift. This is not a guarantee of zero market beta.
- Two-week rebalance, first-Monday anchor per year; actual quantities held between
  decisions. Cross-year intervals can be 7/21 days. Signal cutoff 00UTC,
  sizing at 01UTC, prior-hour VWAP execution proxy at 02UTC.
- Perpetual taker fee 5 bps, no BNB discount; adverse slippage 5/10 bps per fill.
  Funding uses observed rates and a completed-hour mark proxy on pre-fill holdings.
  BTC/ETH spot benchmarks use 10 bps taker + 5 bps slippage per side.
- Required held-price/terminal checks, source-price/fee/funding reconstruction,
  daily-ledger reconciliation and an exact primary financial replay. Historical
  lots/margin/liquidation and order-book impact are not certified.

The conditional cohort's historical publication vintage is unresolved. A matched
momentum-only control has an unverified EOS terminal settlement and cannot support
an alpha claim. Lower simulated MDD does not prove live safety or future returns.

## Reproduce saved results

In WSL, using the existing prepared local dataset and model/source caches:

```bash
conda activate funding-strategy
python scripts/run_continuous_reconstruction.py --stage all
python scripts/run_continuous_reconstruction.py --stage summary
python scripts/publish_continuous_results.py
```

The publisher reads verified outputs; it performs no refit, download or simulation.
Full simulator runs require the ignored local research data and frozen caches; this
repository alone does not supply a one-command fresh-data bootstrap. Never add keys
or market datasets to Git, or delete contracts to bypass validation failures.

- [Results, annual/monthly detail and source provenance](docs/CONTINUOUS_RECONSTRUCTION_RESULTS.md)
- [Simulation runbook, logs and resume behavior](docs/CONTINUOUS_RECONSTRUCTION_RUNBOOK.md)
- [English saved-results notebook](notebooks/continuous_reconstruction_results.ipynb)
- [Experiment 016 registration](experiments/016_continuous_2022_2026.md)
- [Project status / handoff](docs/PROJECT_STATUS.md)

`experiments/` holds registrations; `scripts/` reusable research tools; `src/`
implementation and analysis; `tests/` accounting/regression checks; `docs/`
methodology and conclusions. Source datasets and generated working reports remain
ignored; this README and its figure publish aggregate results only.

## Research archive

- [Completed historical backtests: results, assumptions and commands](docs/FIRST_HISTORICAL_DEVELOPMENT.md)
- [English historical-results notebook](notebooks/first_historical_results.ipynb)
- [Development mark boundary recovery and resumable commands](docs/DEVELOPMENT_MARK_RECOVERY.md)
- [Development warmup continuity and 2022 mark-gap audit](docs/DEVELOPMENT_CONTINUITY_AUDIT.md)
- [Backtest analysis notebook and launch instructions](docs/BACKTEST_NOTEBOOK.md)
- [Notebook source](notebooks/backtest_analysis.ipynb)
- [Momentum and trend-following research landscape](docs/momentum_research_landscape.md)
- [Candidate strategy families before Experiment 001](docs/candidate_strategy_families.md)
- [Project status and handoff](docs/PROJECT_STATUS.md)
- [Historical universe feasibility](docs/historical_universe_feasibility.md)
- [WSL raw-data acquisition commands](docs/USDM_ACQUISITION.md)
- [Post-acquisition quality audit](docs/POST_ACQUISITION_AUDIT.md)
- [Mark-gap source reconciliation](docs/MARK_GAP_RECONCILIATION.md)
- [Mark-gap recovery and versioned partial overlay](docs/MARK_GAP_RECOVERY.md)

- [Research data layer and full-conversion command](docs/RESEARCH_DATA_LAYER.md)
- [Partial lifecycle evidence and remaining gates](docs/LIFECYCLE_REVIEW.md)

- [Research-input readiness and public cap pilots](docs/RESEARCH_INPUT_READINESS.md)

- [Weekly market-cap coverage acquisition](docs/CMC_WEEKLY_COVERAGE.md)

- [Weekly cap identity and coverage audit](docs/CMC_IDENTITY_AUDIT.md)

- [Contract identity evidence and proposed episodes](docs/CONTRACT_IDENTITY_EVIDENCE.md)

- [Identity follow-up and named exclusion decisions](docs/IDENTITY_FOLLOWUP_DECISIONS.md)

- [Full-universe retention screen and candidate lists](docs/FULL_UNIVERSE_RETENTION_SCREEN.md)

- [Daily episode-aware inputs and full-build command](docs/DAILY_RESEARCH_INPUTS.md)

- [Approved chronological research split](docs/RESEARCH_SPLIT.md)

- [Approved weekly baseline, buffer and sizing research sequence](docs/WEEKLY_RESEARCH_SEQUENCE.md)

- [Weekly baseline timing, boundary checks and coverage command](docs/WEEKLY_BASELINE_STAGE0.md)

- [Early history, funding inventory and raw backfill command](docs/HISTORY_EXTENSION.md)

- [Completed early raw integrity, gap and funding audit](docs/EARLY_HISTORY_AUDIT.md)

- [QTUM funding supplement and DEFI/LEND episode checks](docs/EARLY_CASES_REVIEW.md)

- [Completed2020 observation release and daily panel](docs/EARLY_RESEARCH_RELEASE.md)

- [Completed2020 Size inventory and named identity gaps](docs/EARLY_SIZE_INVENTORY.md)

- [Early Size identity decisions and unresolved source gates](docs/EARLY_SIZE_IDENTITIES.md)

- [IOTA alias recovery and UNI futures launch supplement](docs/EARLY_IDENTITY_FOLLOWUP.md)

- [First remaining early identity batch and per-case decisions](docs/EARLY_IDENTITY_BATCH1.md)

- [Second early identity batch and cumulative coverage](docs/EARLY_IDENTITY_BATCH2.md)

- [Third early identity batch, token and migration checks](docs/EARLY_IDENTITY_BATCH3.md)

- [One-command processing and reports for all81 early identifiers](docs/UNIFIED_EARLY_IDENTITY.md)
