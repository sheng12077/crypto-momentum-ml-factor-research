# Experiment 013: frozen two-week candidate, 2024 validation

Registered before implementing or loading 2024 market values, computing features,
training or inspecting performance. The user authorizes opening 2024 after freezing
the candidate. 2022/2023 are development years following Experiments 010--012.
Final 2025-01-01 through 2026-10-31 remains sealed; no paper/live deployment.

## Frozen specification

- Same conditional 37-identifier cohort and dated eligibility as 005/009/010C.
  No expansion, retrospective survivor screening or performance-based exclusions.
- Same five raw inputs: momentum20/60/120, funding7, imbalance7; same original
  LightGBM PARAMS. Size, new filters, buffer, volatility timing and staged entry
  are excluded. Fit once on 2021--2023 samples with feature cutoff and seven-day
  label availability STRICTLY before 2024-01-01. Compute 2023 training labels from
  already verified execution-hour VWAPs; preserve earlier feature/label values.
  No 2024 labels, tuning, early stopping, within-year refit or score recalibration.
- Two-week phase restarts on the first Monday of the year, as in 010C: 2024-01-01,
  then every 14 days, including 2024-12-30 (27 scheduled decisions). Rank top five
  long/bottom five short, equal 10% current NAV each; cash if fewer than 20 eligible.
  Stable identifier ties; hold actual quantities between scheduled decisions.
- Same Monday 00 UTC feature cutoff, 01 UTC sizing from completed hour, 02 UTC
  previous-hour VWAP synthetic execution; initial 100000 USDT, 5 bps taker fee,
  no BNB discount, primary 5 bps extra adverse slippage and 10 bps stress.
  Target gross 100%, net notional zero; no claim of beta neutrality.
- Same funding cashflow and completed-hour mark proxies, fractional eight-decimal
  filters and conditional liquidation/execution limitations. No silent forward
  fills, synthetic settlement, closing-price substitutions or dropping held assets.
  A missing held price or unsupported lifecycle event fails the run and is reported.
- Four fresh-cash Nautilus cases: frozen ML and unfitted momentum60 control, each
  at 5/10 bps. Control uses identical two-week calendar, cohort and allocation.
  One exact primary ML financial replay. Retain every case/failure.
- Same year-end convention: last NAV 2024-12-31 00 UTC; forced close Dec30 23 UTC
  using the previous completed-hour VWAP. Leap year: 366 daily NAV observations,
  365 daily returns; do not claim a complete Jan1-to-next-Jan1 return.
- BTC/ETH actual spot fixed-unit cash-budget holds on the same calendar, 10 bps
  spot taker fee plus 5 bps adverse fills, no leverage or funding.

## Expectations and interpretation gates

Hypothesis: the frozen candidate retains useful net performance beyond development.
Primary gate: net return > 0 AND Sharpe_rf0 > 0 at 5 bps. Cost resilience gate:
net return > 0 at 10 bps. Incremental-model evidence requires primary return AND
Sharpe exceeding matched momentum60. Report each gate separately; failure or mixed
evidence is not a trigger to tune on 2024. These are descriptive decision gates,
not significance tests or live-profitability certification.

Report return, CAGR, volatility, Sharpe, MDD, Calmar, turnover/notional, fees,
funding, BTC/ETH comparisons, all monthly returns and best-month cash-PnL share.
Flag concentration dependence if annual profit > 0 but compounding all months
except the best leaves return <= 0. Report MDD without inventing a post-hoc limit.
Compare 2022/2023 frozen-candidate metrics descriptively, identifying them as
development results. Do not choose a new variant or expose the final holdout.

## Data, integrity and delivery

Scope-filter canonical daily rows to 2023-08-01 <= day < 2025-01-01 before feature
computation; read hourly source months 2024 only plus existing pre-2024 warmup.
Hash source files without loading later market values. Use new versioned outputs;
keep prior caches read-only and verify their hashes and exact preserved rows.

Necessary trade/mark gap repairs are allowed only from official public daily ZIPs
with CHECKSUM: at most 200 source-days/400 requests/64 MiB compressed, 2 MiB per
ZIP/10 MiB per member, >=1 second pacing, stop on 403/418/429. No original value
overwrites. BTC/ETH spot: 24 monthly ZIPs/checksums, <=64 requests/32 MiB compressed.
No API credentials. Stop and report if bounds/evidence fail.

Before historical execution test synthetic 2024 leap-year calendar, two-week phase,
strict training purge, 2023 execution-VWAP labels and future-invariant features.
Require source/code/runtime contracts, finite positive NAV, final flat positions,
fee/funding/notional and marked-equity reconciliation within 0.01 USDT, no held
missing prices, exact financial replay and SHAP additivity error <= 1e-6 on all
2024 scored rows. SHAP is prediction attribution, not causal profit attribution.
Produce English notebook, charts, CSV/JSON, concise result/status with limitations.
Record engineering failures and fixes; no favorable-case deletion or rule changes.
