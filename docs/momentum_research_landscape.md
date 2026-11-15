# Momentum and Trend-Following Research Landscape

Last reviewed: 2026-11-15

## Purpose and scope

This note maps the research relevant to a low-frequency BTC/ETH strategy that
could diversify the existing funding-carry strategy. It is a literature review,
not an experiment registration. No strategy performance was inspected while
preparing it.

The practical research question is narrower than "does momentum exist?":

> Can a simple, point-in-time, volatility-controlled BTC/ETH trend strategy,
> implemented through USD-M perpetuals with realistic funding, execution, and
> liquidation accounting, add value to a funding-carry portfolio?

## Search and screening method

Searches covered journal and publisher pages, author/institution repositories,
NBER, exchange documentation, and recent working-paper indexes. Search concepts
included time-series momentum, trend following, moving averages, volatility
scaling, momentum crashes, cryptocurrency momentum, perpetual futures, funding,
margin, mark price, and liquidation.

Sources were included when they supplied at least one of the following:

- foundational evidence for time-series momentum or trend following;
- a serious replication, decomposition, or counterargument;
- a directly relevant risk-management result;
- crypto spot/futures evidence that distinguishes time-series from
  cross-sectional momentum; or
- primary venue rules needed for an implementable backtest.

Recent unreviewed papers based on large parameter searches were not used to
select rules. Cross-sectional crypto factor papers are retained as context, but
not treated as evidence that a two-asset time-series strategy will work.

## The terminology that matters

### Cross-sectional momentum

Rank many assets against each other, buy relative winners, and sell relative
losers. This requires a sufficiently broad, point-in-time universe. A BTC/ETH
portfolio is too small for a credible first implementation of this family.

### Time-series momentum

Judge each asset against its own past. A typical rule is long after a positive
trailing return and short after a negative trailing return. This is the closest
match to the proposed Strategy B.

### Trend following

The broader implementation family. Return-sign rules, moving-average
crossovers, and price breakouts can all express a related economic idea while
placing different weights on past returns. They should be treated as distinct,
predeclared models rather than a parameter grid.

### Volatility targeting

Scale notional exposure inversely with an ex-ante volatility estimate, subject
to a hard exposure cap. It is a risk-allocation rule, not proof of return
predictability. A valid study must report both the directional signal's value
and the contribution of volatility scaling.

## What the literature establishes

### 1. Trend evidence is broad, but much of the strongest evidence is diversified

Moskowitz, Ooi, and Pedersen (2012) document time-series momentum across 58
liquid equity-index, currency, commodity, and bond futures. Hurst, Ooi, and
Pedersen (2017) extend the historical record and argue that trend following was
profitable across a very long sample and many markets. These results support the
economic plausibility of trend, but their breadth is also a warning: a two-coin
portfolio lacks the cross-market diversification of the original evidence.

### 2. Signal definitions differ, but many belong to the same trend family

Levine and Pedersen (2016) show that generalized trend rules can often be
understood in a unified framework. Other work comparing return-sign momentum
and moving-average rules finds meaningful differences in how they weight price
history. The implication is not to test every variant. It is to choose a small
set of economically distinct rules before seeing results.

### 3. Volatility scaling is useful and a major attribution problem

Moreira and Muir (2017) show that volatility management can improve several
factor portfolios when volatility is not matched by proportionally higher
expected returns. Kim, Tse, and Wald (2016), however, argue that much of the
reported time-series-momentum alpha in futures is driven by volatility scaling
rather than the directional momentum rule. Cederburg et al. (2020) further find
that volatility management does not systematically improve 103 equity
strategies and that reasonable real-time combinations generally disappoint
out-of-sample. Consequently, Strategy B must include unscaled or constant-risk
controls and separately attribute signal, sizing, and cash exposure.

### 4. The statistical evidence is contested

Huang, Li, Wang, and Zhou (2020) re-examine the canonical evidence and find weak
asset-by-asset and out-of-sample return predictability. They also show that a
profitable trading strategy does not by itself prove the specific predictive
regression claimed by the original literature. This is the strongest reason to
avoid presenting a backtest as a universal anomaly proof.

### 5. Momentum can fail violently at turning points

Daniel and Moskowitz (2016) document momentum crashes following market declines,
during high-volatility panic states, and alongside sharp rebounds. Their main
setting is cross-sectional momentum, so the finding cannot be transferred
mechanically to BTC/ETH trend following. It nevertheless identifies the most
important shared failure mode: a short trend position can be hurt severely by a
fast reversal before a slow signal turns. Grobys et al. (2025) document severe
crashes in broad cryptocurrency momentum portfolios, reinforcing the tail-risk
concern, although their construction is not our proposed two-asset time-series
rule.

### 6. Crypto momentum evidence does not directly validate our proposed strategy

Borgards (2021) reports dynamic time-series momentum across twenty
cryptocurrencies and several frequencies, but the turning-point methodology is
materially different from a fixed, executable trailing-return rule. Liu,
Tsyvinski, and Wu (2022) find market, size, and momentum factors in the
cross-section of cryptocurrencies. That is evidence for a broad crypto factor,
not for a two-asset time-series rule. Research on cryptocurrency futures finds
basis to be a stronger cross-sectional return predictor than momentum in its
sample. The crypto literature therefore supports studying momentum, but not
assuming that a BTC/ETH perpetual trend rule has already been validated.

### 7. Perpetual implementation changes the payoff

A perpetual position earns price PnL plus or minus funding and pays trading
costs. Liquidation is triggered from venue-specific margin rules and mark price,
not merely the backtest close. Empirical work on Bitcoin perpetuals links high
leverage to forced liquidation, while Binance documentation confirms that mark
price and maintenance margin drive liquidation. A close-to-close backtest
without mark-price path and margin accounting is therefore insufficient.

## Evidence matrix

| Source | Main contribution | Relevance | Limitation for this project |
| --- | --- | --- | --- |
| Moskowitz, Ooi & Pedersen (2012) | Canonical multi-asset time-series momentum evidence | Foundational signal design | Broad diversified futures universe, not two crypto assets |
| Hurst, Ooi & Pedersen (2017) | Long historical trend-following evidence | Economic plausibility and crisis diversification | Historical reconstruction and diversified universe |
| Levine & Pedersen (2016) | Unifies many trend signal representations | Helps select distinct rule families | Does not identify one universally best rule |
| Kim, Tse & Wald (2016) | Attributes much TSMOM performance to volatility scaling | Requires attribution controls | Traditional futures, not crypto perpetuals |
| Huang et al. (2020) | Challenges pooled-regression and OOS evidence | Core counterevidence | Critiques the general anomaly, not this exact implementation |
| Moreira & Muir (2017) | Evidence for volatility-managed portfolios | Supports ex-ante risk scaling | Not a trend-specific or crypto-specific result |
| Cederburg et al. (2020) | Finds no systematic real-time benefit from volatility management | Core counterevidence for sizing claims | Broad equity strategies, not crypto trend |
| Daniel & Moskowitz (2016) | Documents momentum crash states | Reversal stress tests | Primarily cross-sectional equity momentum |
| Borgards (2021) | Finds dynamic time-series momentum in twenty cryptocurrencies | Direct crypto time-series evidence | Turning-point model differs from fixed tradable rules |
| Liu, Tsyvinski & Wu (2022) | Crypto market, size, and momentum factors | Establishes crypto momentum context | Cross-sectional broad-universe result |
| Grobys et al. (2025) | Finds severe crashes in crypto momentum portfolios | Crypto-specific tail-risk evidence | Broad cross-sectional portfolios, not BTC/ETH TSMOM |
| Chi et al. (2023) | Basis is strongest studied crypto-futures factor | Warns that momentum may be weak in futures | Cross-sectional futures design and different venues/sample |
| Yu et al. (2021) | Liquidation and leverage evidence in Bitcoin perpetuals | Margin and liquidation stress assumptions | BitMEX sample and historically high observed leverage |
| Binance Futures documentation | Mark-price and maintenance-margin mechanics | Defines venue-specific simulation requirements | Rules can change and must be versioned at implementation time |

## The central contradictions

### Is the effect directional predictability or risk scaling?

The foundational studies interpret trend signals as economically meaningful
return predictability. Kim et al. show that volatility scaling can explain much
of the apparent alpha, while Huang et al. question whether asset-level
predictability is statistically strong at all. These claims are not fully
reconcilable. Our design response is attribution, not choosing a side:

1. compare the directional strategy with non-directional or simple exposure
   controls;
2. show results before and after volatility scaling;
3. disclose average cash and gross exposure; and
4. judge Strategy B mainly by portfolio diversification after all costs.

### Does broad historical evidence transfer to BTC/ETH?

Broad futures evidence benefits from many independent trends. BTC and ETH are
highly related and share market structure, so equal weighting does not create
two independent bets. The transfer is a testable hypothesis, not an established
fact.

### Is momentum a hedge in crashes?

Slow trend can profit after persistent declines, but it can lose at the initial
break and at a violent rebound. The correct claim is conditional crisis
diversification, not guaranteed crash protection.

## Crypto-specific threats to validity

- **Look-ahead:** using a daily close to trade at that same close, or using a
  funding payment/rate revision that was not known at decision time.
- **Clock construction:** mixing UTC day boundaries, exchange-local timestamps,
  or incomplete final bars in a 24/7 market.
- **Spot/perpetual mismatch:** generating a signal from a cleaner spot history
  but booking returns on perpetuals without modelling basis and funding.
- **Mark-price gaps:** testing liquidation from last price or daily closes when
  liquidation is driven by the mark-price path.
- **Survivorship and venue bias:** using today's symbols, contract rules, or
  exchange quality throughout history.
- **Funding sign/timing errors:** applying funding to the wrong side, timestamp,
  or notional, especially across changing funding intervals.
- **Turnover understatement:** resizing every day for volatility can trade even
  when the directional state is unchanged.
- **False diversification:** treating BTC and ETH as independent sleeves without
  reporting portfolio concentration and correlation.
- **Parameter selection:** choosing lookbacks, volatility windows, rebalance
  frequency, or flat zones after observing the same history.

## Implications for this repository

The first experiment should remain simple and diagnostic:

- study time-series trend, not cross-sectional crypto momentum;
- use BTC and ETH only because their data and perpetual contracts are the most
  defensible, not because two assets provide broad diversification;
- predeclare at most a small number of distinct signal families;
- cap gross exposure at 1.0 and avoid leverage as a return enhancer;
- separate signal return, volatility-scaling effect, funding, fees, slippage,
  and cash drag;
- execute after the signal timestamp and use mark-price/margin paths for risk;
- include walk-forward or pseudo-OOS reporting even though the historical
  period is no longer blind; and
- evaluate both B alone and its incremental effect on the existing S4 carry
  portfolio.

## Verified primary references

1. Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). [Time Series Momentum](https://doi.org/10.1016/j.jfineco.2011.11.003). *Journal of Financial Economics*, 104(2), 228–250.
2. Hurst, B., Ooi, Y. H., & Pedersen, L. H. (2017). [A Century of Evidence on Trend-Following Investing](https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing). *Journal of Portfolio Management*, 44(1), 15–29.
3. Levine, A., & Pedersen, L. H. (2016). [Which Trend Is Your Friend?](https://rpc.cfainstitute.org/research/financial-analysts-journal/2016/which-trend-is-your-friend). *Financial Analysts Journal*, 72(3), 51–66.
4. Kim, A. Y., Tse, Y., & Wald, J. K. (2016). [Time Series Momentum and Volatility Scaling](https://doi.org/10.1016/j.finmar.2016.05.003). *Journal of Financial Markets*, 30, 103–124.
5. Huang, D., Li, J., Wang, L., & Zhou, G. (2020). [Time Series Momentum: Is It There?](https://doi.org/10.1016/j.jfineco.2019.08.004). *Journal of Financial Economics*, 135(3), 774–794.
6. Moreira, A., & Muir, T. (2017). [Volatility-Managed Portfolios](https://doi.org/10.1111/jofi.12513). *Journal of Finance*, 72(4), 1611–1644.
7. Cederburg, S., O'Doherty, M. S., Wang, F., & Yan, X. (2020). [On the Performance of Volatility-Managed Portfolios](https://doi.org/10.1016/j.jfineco.2020.04.015). *Journal of Financial Economics*, 138(1), 95–117.
8. Daniel, K., & Moskowitz, T. J. (2016). [Momentum Crashes](https://doi.org/10.1016/j.jfineco.2015.12.002). *Journal of Financial Economics*, 122(2), 221–247.
9. Borgards, O. (2021). [Dynamic Time Series Momentum of Cryptocurrencies](https://doi.org/10.1016/j.najef.2021.101428). *North American Journal of Economics and Finance*, 57, 101428.
10. Liu, Y., Tsyvinski, A., & Wu, X. (2022). [Common Risk Factors in Cryptocurrency](https://doi.org/10.1111/jofi.13119). *Journal of Finance*, 77(2), 1133–1177.
11. Grobys, K., Kolari, J. W., Sandretto, D., Shahzad, S. J. H., & Äijö, J. (2025). [Cryptocurrency Momentum Has (Not) Its Moments](https://doi.org/10.1007/s11408-025-00474-9). *Financial Markets and Portfolio Management*, 39(4), 443–476.
12. Chi, Y., Hao, W., Hu, J., & Ran, Z. (2023). [An Empirical Investigation on Risk Factors in Cryptocurrency Futures](https://doi.org/10.1002/fut.22425). *Journal of Futures Markets*, 43(5), 600–628.
13. Yu, M., et al. (2021). [Liquidation, Leverage and Optimal Margin in Bitcoin Futures Markets](https://doi.org/10.1080/00036846.2021.1922597). *Applied Economics*, 53(47), 5415–5428.
14. Binance. [Futures Liquidation Protocols](https://www.binance.com/en/support/faq/detail/360033525271).
15. Binance. [How to Calculate Liquidation Price of USD-M Futures Contracts](https://www.binance.com/en/support/faq/detail/b3c689c1f50a44cabb3a84e663b81d93).

## Knowledge gaps we must answer ourselves

1. Whether a two-asset BTC/ETH implementation retains any benefit after funding,
   turnover, slippage, and conservative exposure caps.
2. Whether Strategy B helps specifically during S4's bear and non-positive
   funding regimes rather than merely adding standalone return.
3. Whether apparent improvement comes from trend direction, volatility timing,
   or simply holding less risk and more cash.
4. Whether hourly mark-price data are complete enough to support defensible
   liquidation-path testing, and how missing marks will be handled.
5. How sensitive the conclusion is to exchange rules and stress costs without
   turning those checks into a parameter search.
