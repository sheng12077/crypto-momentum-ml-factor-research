# Frozen 2024 validation and failure attribution

Experiment013 is complete: four cases, one identical primary financial replay,
5691 purged training rows, 1932 scored 2024 rows, verified SHAP and report.
The two-week/no-buffer/equal-weight candidate fails all three registered 2024
performance gates. 2022/2023 are development years, not untouched OOS. Final
2025--October2026 remains sealed. This does not establish live suitability.

## Frozen validation outcome

| 2024 case | Net return | Sharpe rf0 | MDD |
|---|---:|---:|---:|
| ML,5bps | -12.7072% | -0.4995 | -21.3715% |
| ML,10bps | -14.5122% | -0.5925 | -22.2856% |
| Momentum60,5bps | -16.7453% | -0.3422 | -24.8815% |
| Momentum60,10bps | -17.8571% | -0.3796 | -25.0333% |
| BTC spot hold | +116.4706% | 1.7184 | -26.1514% |
| ETH spot hold | +44.9846% | 0.8914 | -45.2561% |

Spot holds have different directional exposure. ML reduces loss/MDD relative to
momentum60, but Sharpe is worse; it is not superior on all risk-adjusted metrics.
Calendar:366NAV snapshots/365returns, last valuation Dec31 00UTC, forced close
Dec30 23UTC. Initial100000USDT. Fees5bps plus listed extra adverse slippage;
spot benchmarks10bps fee plus5bps fills.

## Ledger diagnosis: primary ML

| Additive contribution | USDT | Percentage points of initial NAV |
|---|---:|---:|
| Source-VWAP price PnL at actual fixed quantities | -8378.49 | -8.3785 |
| Adverse-fill displacement | -1862.11 | -1.8621 |
| Commissions | -1862.11 | -1.8621 |
| Recorded funding cashflows | -604.52 | -0.6045 |
| Net PnL | -12707.23 | -12.7072 |

Displacement is actual-fill-versus-source-VWAP accounting at identical quantities,
not a hypothetical zero-cost portfolio rerun. Actual price PnL already contains
slippage; do not subtract displacement twice. Removing fee/funding/slippage entries
does not turn same-quantity price selection positive.

| Held side | Price PnL including slippage | Funding | Fees | Net PnL |
|---|---:|---:|---:|---:|
| Long | +17658.73 | -5953.82 | 910.85 | +10794.06 |
| Short | -27899.33 | +5349.30 | 951.26 | -23501.29 |

Long gains fail to offset short losses. Net-notional-zero exposure does not imply
beta neutrality, nor does a low cross-sectional score predict negative absolute
return. Positive long-side attribution is not evidence that deleting shorts would
produce a viable long-only strategy: capital/exposure/holdings would change.

## Months and assets

| Month | Long net contribution | Short net contribution | Portfolio return |
|---|---:|---:|---:|
| February | +13077.36 | -14948.89 | -1.8861% |
| March | +273.56 | -10480.82 | -10.4847% |
| June | -4579.96 | +15973.65 | +13.9241% |
| November | +29007.48 | -32434.08 | -3.6795% |

Only4of12months profitable. March contributes -10207.27USDT (80.33% of net annual
loss, a ratio of signed contributions, not an independent risk measure). Excluding
March leaves -2.4829% compounded return; the failure is not solely March. June is
the best month: excluding it leaves -23.3764% compounded return. This exclusion is
descriptive, not a tradable rule or evidence of a recurring June seasonal effect.

Largest negative annual asset/side contributions include ATOM short -6828.49,
COMP short -6697.30, DASH short -6614.85, SNX long -6034.15 and QTUM short -5993.08.
Worst-March combined-asset contributions include WAVES -2404.91 and DASH -2127.25.
Losses span multiple names; no retrospective asset exclusions were tested.

The combination of large short losses in positive BTC/ETH months and short-led
June profit is consistent with regime sensitivity. It does not prove that market
beta alone caused losses or that a trend timing overlay would fix them. No
causal exposure estimate or overlay experiment was performed.

## Model attribution and unresolved hypotheses

Mean absolute SHAP shares over all2024predictions:Funding43.84%, combined momentum
45.41%, imbalance10.75%. These are shares of attribution magnitudes, not model
weights, forecast accuracy or shares of profit. Funding matters to predictions;
its actual annual net cashflow is only -604.52USDT. Neither observation proves
Funding caused the trading losses.

Selected shorts have average positive20day momentum (+9.15%), and selected longs
+6.21%; the nonlinear model ranks relative forecasts rather than requiring bearish
short signals. These are unweighted selection-date averages, not holding-period
returns or a tested absolute-direction filter. In135short selection slots,
22have positive model forecast scores (spread across7of27decision dates). The
rule always selects bottom five, even when some forecasts are positive. These
scores are not validated calibrated expected returns, and this observation does
not establish that a negative-score filter would work. The seven-day prediction label
with fourteen-day trading cadence is an existing design mismatch worth noting;
its causal contribution is not identified by this diagnostic.

## Reproducibility and next decision

Run `python scripts/attribute_validation_2024.py` to reproduce descriptive
reconstruction only. No fits, downloads, 2024 labels or historical simulations.
Tables and JSON: data/interim/validation_2024/v20261121_002/attribution_v001/.
Figures: reports/figures/validation_2024/*_attribution.png.

Synthetic reversal/fee/funding fixture and corrupt-NAV rejection:5tests passed.
Both strategies reconcile every daily NAV change and cumulative NAV within
0.01USDT (actual maxima below1e-6); all funding quantities, fees and notionals
reconcile; final positions flat and saved input hashes unchanged. Original
financial results are read-only. Hash bindings and script SHA accompany outputs.

Supported conclusion: the frozen candidate did not generalize successfully to
2024. Costs amplify a negative same-quantity price component; short losses
outweigh long gains. Keep current research concluded as failed validation; do not
promote to paper/live or tune a timing/short-selection rule on this year and call
it OOS. Any new hypothesis needs a separately registered study; final holdout
opening remains a separate user decision.
