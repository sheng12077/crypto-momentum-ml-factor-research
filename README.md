# Crypto Cross-Sectional Factor Research

A reproducible, medium-frequency crypto long/short research project using annual
LightGBM forecasts and NautilusTrader execution/accounting. Momentum, funding and
aggressive-buy/sell imbalance rank a conditional 37-asset USDT-perpetual cohort.

**Current status: completed retrospective backtest; no live profitability claim.**
The uninterrupted 2022--October 2026 account is net profitable with lower historical
volatility/drawdown than BTC/ETH holding, but monthly consistency is weak and results
are substantially stronger in development years. Paper/live trading is not implemented
or certified by these results.

## Full period versus original OOS

| Period | Role | Interpretation |
| --- | --- | --- |
| 2022--2023 | Development / selection | Used to inform strategy and execution choices |
| 2024 | Frozen validation | Revealed before the final holdout |
| 2025--October 2026 | Original final OOS; now disclosed | Protocol015 separate account; frozen annual expanding fits |
| 2022--October 2026 | Full retrospective reconstruction | Protocol016 registered after all annual results were observed |

| Account / period | Return | CAGR | Sharpe (rf=0) | MDD |
| --- | --- | --- | --- | --- |
| Full path (2022--2026) | +84.06% | +13.45% | 0.645 | -26.77% |
| Original OOS account (2025--2026) | +16.31% | +8.61% | 0.435 | -24.79% |
| OOS-date slice of full path; carry-in diagnostic | +24.08% | +12.51% | 0.557 | -24.79% |

All primary rows include 5 bps adverse slippage plus 5 bps perpetual taker fees and
Funding. The original OOS account starts with USDT 100,000 in cash on Jan 1, 2025;
it does not inherit 2024 positions. The full-path diagnostic carries positions/capital
from 2024 and is rebased at exactly the same Jan 1, 2025 NAV timestamp. It is **not**
a substitute OOS result. The +84.06% whole-period result is also **not all OOS**.
All comparisons end Oct 31, 2026 00:00 UTC; the last civil day is not included.
Development years may contain chronological forward forecasts but were used for
rule selection; that does not make them the clean final test.

![Full path and original OOS equity](docs/assets/full_period_vs_oos.png)


Original OOS benchmarks and monthly results: [detailed period disclosure](docs/CONTINUOUS_RECONSTRUCTION_RESULTS.md#full-period-versus-original-oos).


## Continuous performance (full retrospective account)

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
  decisions. Cross-year intervals can be 7/21 days. Signal cutoff 00:00 UTC,
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

## Project structure

```text
src/momentum_data/
    data/          # hourly stores, benchmarks and complete input checks
    features/      # past-only factor definitions and history validation
    models/        # frozen annual model/training/prediction/SHAP verification
    portfolio/     # ranking and two-week portfolio schedule
    backtest/      # Nautilus execution, Funding, independent ledger audit
    reporting/     # metrics, publication and monthly heatmap
    cli.py         # public commands
scripts/           # three thin compatibility/demo entry points
config/            # named frozen-run paths and execution assumptions
notebooks/         # current English results reader
research/legacy/   # preserved earlier research layout and frozen source bytes
experiments/       # original preregistrations
```

[Architecture and migration notes](docs/PROJECT_STRUCTURE.md) explain which paths
are active, how frozen contracts survive relocation, and how historical tools are
kept separate. The public package does not import legacy scripts. Archived model
training/acquisition pipelines remain research evidence; the current CLI verifies
and replays the existing frozen model caches, rather than promising a fresh-data bootstrap.

## Install and run without market data

From the repository root on Linux/WSL with Python 3.13:

```bash
python -m pip install -r requirements/research-runtime-py313.txt
python -m pip install -e ".[research,dev]"
python -m momentum_data --help
python -m momentum_data smoke
python -m pytest tests -q
```

The smoke example creates a synthetic cross-year position and verifies its cash
and Funding. It requires no API key, exchange connection or market dataset and
makes no profitability claim. Runtime pins cover the current top-level packages,
not a fully transitive environment lock. Historical lockfiles are retained separately.

## Reproduce saved results

With the existing ignored local dataset and frozen caches available:

```bash
python -m momentum_data verify
python -m momentum_data replay
python -m momentum_data summary
python -m momentum_data publish
```

`replay` runs both cost cases and the primary replay through the reorganized engine
in a separate output directory; every financial SHA256 must equal the frozen result.
It never overwrites the original case files. The new package also binds its own
source/configuration contract. Local paths default to this checkout; set
`MOMENTUM_PROJECT_ROOT` and, if needed, `MOMENTUM_DATA_ROOT` before importing the
package to point at another research checkout/data root.

The original convenience commands remain available:

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

`experiments/` holds registrations; `scripts/` contains thin launchers; `src/`
holds the independent package; `tests/` current accounting/interface checks; `docs/`
methodology and conclusions. Source datasets and generated working reports remain
ignored; this README and its figure publish aggregate results only.

## Research archive

- [Completed historical backtests: results, assumptions and commands](research/legacy/docs/FIRST_HISTORICAL_DEVELOPMENT.md)
- [English historical-results notebook](research/legacy/notebooks/first_historical_results.ipynb)
- [Development mark boundary recovery and resumable commands](research/legacy/docs/DEVELOPMENT_MARK_RECOVERY.md)
- [Development warmup continuity and 2022 mark-gap audit](research/legacy/docs/DEVELOPMENT_CONTINUITY_AUDIT.md)
- [Backtest analysis notebook and launch instructions](research/legacy/docs/BACKTEST_NOTEBOOK.md)
- [Notebook source](research/legacy/notebooks/backtest_analysis.ipynb)
- [Momentum and trend-following research landscape](research/legacy/docs/momentum_research_landscape.md)
- [Candidate strategy families before Experiment 001](research/legacy/docs/candidate_strategy_families.md)
- [Project status and handoff](docs/PROJECT_STATUS.md)
- [Historical universe feasibility](research/legacy/docs/historical_universe_feasibility.md)
- [WSL raw-data acquisition commands](research/legacy/docs/USDM_ACQUISITION.md)
- [Post-acquisition quality audit](research/legacy/docs/POST_ACQUISITION_AUDIT.md)
- [Mark-gap source reconciliation](research/legacy/docs/MARK_GAP_RECONCILIATION.md)
- [Mark-gap recovery and versioned partial overlay](research/legacy/docs/MARK_GAP_RECOVERY.md)

- [Research data layer and full-conversion command](research/legacy/docs/RESEARCH_DATA_LAYER.md)
- [Partial lifecycle evidence and remaining gates](research/legacy/docs/LIFECYCLE_REVIEW.md)

- [Research-input readiness and public cap pilots](research/legacy/docs/RESEARCH_INPUT_READINESS.md)

- [Weekly market-cap coverage acquisition](research/legacy/docs/CMC_WEEKLY_COVERAGE.md)

- [Weekly cap identity and coverage audit](research/legacy/docs/CMC_IDENTITY_AUDIT.md)

- [Contract identity evidence and proposed episodes](research/legacy/docs/CONTRACT_IDENTITY_EVIDENCE.md)

- [Identity follow-up and named exclusion decisions](research/legacy/docs/IDENTITY_FOLLOWUP_DECISIONS.md)

- [Full-universe retention screen and candidate lists](research/legacy/docs/FULL_UNIVERSE_RETENTION_SCREEN.md)

- [Daily episode-aware inputs and full-build command](research/legacy/docs/DAILY_RESEARCH_INPUTS.md)

- [Approved chronological research split](research/legacy/docs/RESEARCH_SPLIT.md)

- [Approved weekly baseline, buffer and sizing research sequence](research/legacy/docs/WEEKLY_RESEARCH_SEQUENCE.md)

- [Weekly baseline timing, boundary checks and coverage command](research/legacy/docs/WEEKLY_BASELINE_STAGE0.md)

- [Early history, funding inventory and raw backfill command](research/legacy/docs/HISTORY_EXTENSION.md)

- [Completed early raw integrity, gap and funding audit](research/legacy/docs/EARLY_HISTORY_AUDIT.md)

- [QTUM funding supplement and DEFI/LEND episode checks](research/legacy/docs/EARLY_CASES_REVIEW.md)

- [Completed2020 observation release and daily panel](research/legacy/docs/EARLY_RESEARCH_RELEASE.md)

- [Completed2020 Size inventory and named identity gaps](research/legacy/docs/EARLY_SIZE_INVENTORY.md)

- [Early Size identity decisions and unresolved source gates](research/legacy/docs/EARLY_SIZE_IDENTITIES.md)

- [IOTA alias recovery and UNI futures launch supplement](research/legacy/docs/EARLY_IDENTITY_FOLLOWUP.md)

- [First remaining early identity batch and per-case decisions](research/legacy/docs/EARLY_IDENTITY_BATCH1.md)

- [Second early identity batch and cumulative coverage](research/legacy/docs/EARLY_IDENTITY_BATCH2.md)

- [Third early identity batch, token and migration checks](research/legacy/docs/EARLY_IDENTITY_BATCH3.md)

- [One-command processing and reports for all81 early identifiers](research/legacy/docs/UNIFIED_EARLY_IDENTITY.md)
