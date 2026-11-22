# Dynamic-universe 2024 validation analysis

Reviewed 2026-11-22. Existing completed run:
`data/processed/dynamic_2024/a51e40a2229536b092cf/`.
Train 2021–2023 / trade 2024. No new fit, simulation, tuning or experiment.
All 30 cases, primary replay and independent audit passed. Financial reliability
does not establish predictive usefulness. Annual account starts with 100000 USDT.

## Matched controls and costs

| Case | Return | Sharpe rf=0 | MDD |
| --- | ---: | ---: | ---: |
| LightGBM, 5 bps slippage | -7.19% | -0.006 | -37.75% |
| LightGBM, 10 bps | -9.40% | -0.069 | -38.44% |
| LightGBM, 20 bps | -13.66% | -0.194 | -39.81% |
| Momentum60, 5 bps | -27.50% | -0.559 | -42.21% |
| Equal factor-group score, 5 bps | +116.62% | 1.941 | -31.23% |
| Equal factor-group score, 10 bps | +111.93% | 1.891 | -31.55% |
| Equal factor-group score, 20 bps | +102.81% | 1.791 | -32.51% |
| BTC spot holding | +116.47% | 1.718 | -26.15% |
| ETH spot holding | +44.98% | 0.891 | -45.26% |

The equal-group control averages cross-sectional percentile ranks of three groups:
mean momentum20/60/120 rank, inverse funding7 rank, and imbalance7 rank.
Both control and model use equal position weights, the same eligible inputs and
two-week schedule. This is a scoring comparison, not a portfolio-weighting test.
The simple control is stronger in this year; this does not prove permanent
superiority or that any individual factor is independently profitable.

## Long/short ledger reconciliation

Values below are USDT, with position-side realized price PnL including simulated
slippage. Fees and funding are separately attributed. All positions are closed;
side sums reconcile with each case's ending NAV minus initial capital within 0.01.

| Case / side | Price PnL | Fees | Funding | Net PnL |
| --- | ---: | ---: | ---: | ---: |
| Model long | 30633.56 | 986.56 | -6439.15 | 23207.84 |
| Model short | -36801.33 | 990.48 | 7389.85 | -30401.97 |
| Equal-group long | 90688.91 | 1895.69 | 3882.75 | 92675.97 |
| Equal-group short | 7188.91 | 1687.53 | 18446.70 | 23948.07 |

Model price PnL totals -6167.77 before commissions and funding; after subtracting
1977.04 commissions and adding 950.69 funding, net PnL is -7194.12. Removing fees
alone would not make it profitable, holding fills fixed. No zero-slippage simulation
was performed. Larger slippage worsens results, but fees alone are not the failure.
The equal-group case pays higher total commissions (3583.22) and remains profitable.

The model's short losses dominate its net loss; weaker long returns also explain
part of its gap to the equal-group control. Equal-group shorts have positive price
PnL and positive funding. The results do not support blaming all short exposure
or market direction alone. Ex-post deleting shorts is not a tested long-only strategy.

## Timing and concentration

- Model: 5 positive months; Jan -3.79%, Feb -10.04%, Mar -6.91%, Apr -13.04%.
  Worst daily-NAV drawdown is from Jan 4 peak to Jun 25 trough (-37.75%).
- Model best month: December +21.00%. Compounding the other monthly returns
  gives -23.30%; this is a diagnostic, not a separately simulated account.
- Equal-group: 9 positive months; best February +29.42%; excluding that month
  still gives +67.38%. Its MDD is nevertheless substantial: -31.23%, Jul 19–Sep 28.
- Momentum60: 4 positive months, -31.93% excluding its best month.

Model worst net asset contributors (all long/short episodes combined): XVG -8125,
PEOPLE -7860, AR -7759, GRT -7192 and BIGTIME -6479 USDT. Best: COTI +12437,
WLD +9631 and ALT +8266. These are attribution, not instructions to blacklist assets.

Within model price PnL, REEF shorts lose about 17632 USDT; AR shorts 7869,
GRT shorts 7251, XVG shorts 7222, RLC shorts 6497. REEF's total net asset
contribution is only -6421 because other episodes and costs/funding offset part
of the short price loss. Do not equate one side's gross loss to total asset net PnL.
Equal-group also has large REEF short losses (21571 price PnL), yet is profitable
overall. Avoid treating one ticker as the universal explanation.

## Interpretation and next decisions

Observed: model ranking fails to outperform a simple matched factor score in 2024,
and 12/20 random seeds have higher returns, 11/20 higher Sharpe. The random median
return is +3.37%. Twenty controls are descriptive, not a formal significance test.

Mean absolute grouped SHAP: funding 0.01154, momentum 0.00934, imbalance 0.00639.
These describe model output sensitivity, not realized alpha or causal attribution.
They do not establish that funding caused the failure or should be removed.

Unproven mechanisms worth testing separately: nonstationary learned relationships,
fragile short-tail ranking, seven-day gross-price labels versus two-week holdings
and net costs. These are hypotheses; this attribution does not distinguish them.

Do not tune weights immediately to repair this year. Keep the model and equal-group
baseline as distinct registered candidates if evaluating the original final-OOS
interval next. A later position-weighting experiment should hold rankings fixed,
be separately registered and distinguish factor-score weights from position weights.
No live/paper readiness conclusion is supported by these historical results alone.

Sources: saved report/all_case_metrics.csv, monthly_returns.csv, asset_attribution.csv,
side_attribution.csv, cost_and_random_comparison.json; model/shap_group_importance.csv;
existing fills.csv, funding.csv and engine_daily.csv for the three 5 bps controls.
No source or result artifact was modified.
