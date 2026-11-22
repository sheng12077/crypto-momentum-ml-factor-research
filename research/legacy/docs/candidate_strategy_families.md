# Candidate Strategy Families Before Experiment 001

Status: discussion draft; no rules or thresholds are frozen.

This document narrows the literature into a small set of preregistrable models.
It deliberately contains no backtest results and does not authorize performance
inspection.

## Candidate A: single-horizon return sign

For each asset, use the sign of one trailing cumulative return to choose Long or
Short. Add Flat only through a rule that can be fixed without calibration, or
omit Flat in the benchmark.

**Why include it:** It is the cleanest interpretation of canonical time-series
momentum and the easiest model to audit.

**Main weakness:** One arbitrary horizon can dominate the conclusion, and a
slow signal is vulnerable at turning points.

**Best role:** transparent benchmark, not automatically the promoted strategy.

## Candidate B: fixed dual-horizon consensus

Compute one medium and one slow return-sign signal. Hold Long when both are
positive, Short when both are negative, and Flat when they disagree. Fix both
horizons from literature and economic reasoning before performance inspection.

**Why include it:** It implements the requested Long/Short/Flat state without
fitting an indifference band and naturally reduces exposure during ambiguous
transitions.

**Main weakness:** The Flat state can look good merely because it lowers average
risk. Cash exposure and risk-matched comparisons are mandatory.

**Best role:** leading candidate for the first confirmatory experiment.

## Candidate C: fixed moving-average crossover

Use one predetermined fast/slow moving-average pair to select Long or Short,
with an optional Flat state only when exactly equal or through a preregistered
non-fitted rule.

**Why include it:** Moving-average rules weight recent history differently from
a simple endpoint return and are a distinct, widely studied trend expression.

**Main weakness:** The space of possible pairs is enormous. Testing a grid and
choosing the best pair would immediately turn the first experiment into data
mining.

**Best role:** one robustness comparator if the exact pair is justified before
results, not a family to optimize.

## Not recommended for Experiment 001

- cross-sectional momentum across BTC and ETH;
- on-chain predictors or alternative-data factor models;
- dynamic regime classifiers;
- RSI, ATR, breakout, moving-average, and return-sign combinations in one search;
- machine learning or meta-labeling;
- optimized stop-loss, take-profit, or drawdown filters;
- funding-conditioned entry rules; or
- selecting a horizon separately for BTC and ETH.

These may be valid later research topics, but each creates additional degrees of
freedom before the basic trend hypothesis has been tested.

## Common risk wrapper to discuss before preregistration

The same wrapper should be applied to all directional candidates so the signal
comparison is fair:

- separate BTC and ETH sleeves with fixed ex-ante weights;
- point-in-time realized-volatility estimate;
- fixed portfolio volatility target;
- hard gross-exposure cap of 1.0;
- no leverage used to raise return above the cap;
- signal calculated only from completed bars;
- execution no earlier than the next declared executable timestamp;
- fixed rebalance rule that does not resize continuously without accounting for
  turnover;
- taker fee, slippage, funding, and stress-cost scenarios reported separately;
- venue-specific maintenance margin and mark-price liquidation checks; and
- forced Flat state if required data are unavailable under the preregistered
  missing-data policy.

## Required attribution controls

Every candidate should be compared with controls that answer different
questions:

| Control | Question answered |
| --- | --- |
| Buy-and-hold BTC/ETH at the same capital cap | Is the result just crypto beta? |
| Directional rule without volatility scaling | Does the signal add value before sizing? |
| Volatility-scaled long-only exposure | Is the result mainly volatility timing? |
| Cash | Does the strategy clear the project's 4% hurdle? |
| S4 carry alone | Does B improve the existing research baseline? |
| B alone and fixed-weight S4+B | Is diversification economically useful? |

## Current recommendation

Use Candidate B as the proposed primary model, Candidate A as the canonical
benchmark, and at most one preregistered Candidate C implementation as a signal
family robustness check. The experiment should not select whichever candidate
has the highest historical Sharpe. Promotion should be based on frozen
acceptance criteria, with the combined S4+B portfolio given more weight than B's
standalone CAGR.

Before Experiment 001 is registered, the following still require explicit
decisions:

1. exact medium and slow horizons;
2. daily versus weekly state changes and resizing;
3. volatility estimator, window, target, and cap behavior;
4. BTC/ETH sleeve weights and whether correlated exposure needs a portfolio cap;
5. execution timestamp and price hierarchy;
6. base fee/slippage and stress assumptions;
7. funding timestamp/sign conventions;
8. isolated versus cross-margin simulation and collateral allocation;
9. missing mark-price policy;
10. walk-forward or pseudo-OOS reporting windows; and
11. standalone and S4+B acceptance thresholds.
