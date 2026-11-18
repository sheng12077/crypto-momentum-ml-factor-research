# Approved weekly research sequence

User approved this sequence on 2026-11-18: weekly baseline, independent buffer
experiment, then position-adjustment experiment. This records the research
direction; it is not a complete experiment preregistration or performance result.
The approved windows in [RESEARCH_SPLIT.md](RESEARCH_SPLIT.md) remain unchanged.

## Layer 1: weekly baseline

Use a one-week forward-return prediction horizon and weekly scheduled portfolio
reconstruction as the baseline. Stage0 subsequently fixes a raw proxy-return
target and hourly VWAP clock in [WEEKLY_BASELINE_STAGE0.md](WEEKLY_BASELINE_STAGE0.md). Features
may include 20/60/120-day momentum components, Size, observed funding and taker
imbalance; final transformations and model specification are not frozen.

No rank buffer or staged position adjustment in this baseline. Establish the
prediction and trading/accounting rules before attributing improvements to later
layers. Neither market neutrality nor profitability follows from a ranking alone.

## Layer 2: independent rank-buffer experiment

Compare identical predictions, universe, portfolio budget, costs and evaluation
dates with and without a stricter entry threshold than retention threshold.
The clean primary buffer comparison keeps the same weekly decision schedule.
Daily monitoring can be a separately declared frequency comparison; changing
frequency and adding a buffer together cannot isolate the buffer's contribution.

Define long and short entry/exit bands, ties, replacement/capacity handling and
forced exits before implementation. A rank buffer does not by itself prevent
turnover from reweighting existing names. Record entry/exit turnover and resizing
turnover separately; model delisting and forced-exit behavior explicitly.

Expectation to preregister: the buffer reduces unnecessary turnover; benefit
must be assessed after trading costs and funding cashflows, not inferred from
lower turnover alone. Numerical acceptance thresholds are still pending.

## Layer 3: position-adjustment experiment

Only after the earlier layers are specified, hold the signal/selection rule
constant and compare immediate versus partial movement toward target positions.
20/60/120 consensus-based sizing is a candidate, not an approved fixed rule.
Keep explicit gross/net exposure and risk comparisons: lower risk by holding less
is not automatically an improvement in signal quality. Costs and time-to-target
must be counted. Adjustment speed and acceptance thresholds remain undecided.

## Literature anchors and limits

- Liu, Tsyvinski and Wu (2022), *Common Risk Factors in Cryptocurrency*, Journal
  of Finance, DOI [10.1111/jofi.13119](https://doi.org/10.1111/jofi.13119).
  The [2019 author working paper](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
  describes weekly sorting and subsequent-week portfolio returns. Supports a
  weekly research benchmark, not net profitability in perpetual futures.
- Novy-Marx and Velikov (2016), *A Taxonomy of Anomalies and Their Trading Costs*,
  Review of Financial Studies, DOI [10.1093/rfs/hhv063](https://doi.org/10.1093/rfs/hhv063).
  Buy/hold spreads mitigate costs in their equity evidence. Crypto transfer and
  specific thresholds need testing; daily buffer superiority is not established.
- Garleanu and Pedersen (2013), *Dynamic Trading with Predictable Returns and
  Transaction Costs*, Journal of Finance, DOI
  [10.1111/jofi.12080](https://doi.org/10.1111/jofi.12080).
  Their model links signal decay and costs to partial trading toward an aim
  portfolio; it does not validate three equal 20/60/120 entry increments.
- Gu, Kelly and Xiu (2020), *Empirical Asset Pricing via Machine Learning*, Review
  of Financial Studies, DOI [10.1093/rfs/hhaa009](https://doi.org/10.1093/rfs/hhaa009).
  Chronological training/validation/testing and predictive model comparisons;
  monthly equity evidence does not choose a crypto prediction horizon.

## Before implementation or performance experiments

Resolve target definition, exact schedule/latency, historical universe and Size
assumption, missingness, holdings/weighting/exposures, model/baselines, refit,
funding/terminal accounting, fees/slippage and acceptance thresholds. Complete
the experiment preregistration in a standalone main commit first. Do not choose
these settings from final OOS or future universe membership. Strict Size vintage
and full historical eligibility remain unproven. No performance run is authorized
by this incomplete design record; no final OOS was inspected.
