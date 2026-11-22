# Liu and Tsyvinski (2021): project research note

## Material passport

- Reviewed: 2026-11-18. Scope: supplied FINAL published main article, all 39
  journal pages (2689-2727), plus JSTOR cover (40 PDF pages total).
- Article: Yukun Liu and Aleh Tsyvinski, Risks and Returns of Cryptocurrency,
  The Review of Financial Studies 34(6), 2689-2727 (2021).
- DOI: https://doi.org/10.1093/rfs/hhaa113. Online publication: 2020-09-26.
- Supplied file: Liu-RisksReturnsCryptocurrency-2021.pdf; SHA256: c57aafbf6f96ddd5a4ab574556b62ce30059ece0f457614a1a03e76fa2470927.
- Internet Appendix, original replication code and historical vendor snapshots
  were NOT supplied/reviewed. Results discussed only in that appendix are not
  independently verified. This review does not reproduce numerical findings.
- Main text extracted; Table 6 and the section 4.2 portfolio passage visually
  verified against rendered PDF pages 19 and 33. Page 20 also rendered.
- No factor computation, model fit, backtest, portfolio selection or OOS reveal.

## Supported conclusion and scope

The paper supports studying cryptocurrency-specific momentum and attention,
including weekly forecast/holding horizons. It does NOT identify our optimal
holding period, justify 20/60/120-day equal votes, validate LightGBM, specify a
ranking buffer, or establish that our four-factor Binance perpetual strategy
will earn implementable net returns.

The headline tests concern an aggregate spot cryptocurrency index through 2018.
Section 4.2 separately describes a small-universe directional long/short portfolio.
Do not conflate either with our proposed cross-sectional four-factor ranking.
This is not Common Risk Factors in Cryptocurrency (Liu, Tsyvinski and Wu).

## Data and construction (section 1, pp. 2690, 2694-2695)

- Main aggregate index covers 2011-01-01 through 2018-12-31. CMC multi-coin
  history starts 2013-04-29; earlier index observations are spliced Bitcoin
  returns, not a broad multi-coin market. The introduction reports 1707 coins.
- Uses CMC daily price/volume/market capitalization, requires these fields and
  excludes market caps below USD1 million; index is value weighted.
- CMC includes inactive/defunct coins, helping survivorship coverage. This does
  not independently establish point-in-time vendor snapshots, lagged index
  weights, executable prices, borrow availability or delisting cashflows.
- Source prices aggregate exchanges; they are not executable Binance USD-M
  perpetual prices. Our universe, era, venue, funding and costs differ.
- Network measures largely use Bitcoin adoption proxies. Attention includes
  Bitcoin Google searches and Twitter counts. Mining/electricity and traditional
  factor data support other tests, not a fully specified tradable four-factor model.

## Momentum test (section 2.3.1, Table 6, pp. 2705-2707)

- Predictor Rt: current WEEKLY aggregate coin market return. It is not a
  20/60/120-day return-sign ensemble.
- Outcome: FUTURE cumulative aggregate returns at horizons 1 through 8 weeks;
  Table 6 displays 1,2,3,4,6,8 weeks. This is a multi-horizon predictability
  exercise, not proof that one horizon is economically optimal after costs.
- One-week coefficient = 0.20, t=2.53, R-squared=0.04. A 16.50 percentage-point
  predictor standard deviation times 0.20 corresponds to 3.30 percentage points
  of fitted next-week return; this is not a net trading return.
- Text reports 5%-level cumulative predictability at 1-5 weeks; 6-8 weeks are
  weaker (10% level). Do not describe all horizons as equally strong.
- Main text says its appendix's NON-cumulative forecasts are significant at
  1-5 weeks; 6-7 weeks are positive/insignificant and week 8 negative/insignificant.
  Those appendix tables were not inspected. Cumulative 8-week significance
  cannot establish an incremental week-8 edge.
- Weekly boundary is given in the article as Sunday 11:59:59 UTD (the printed
  acronym/time convention needs verification before implementation). Never
  translate this automatically into an exact UTC executable boundary.

### Sorting and the no-lookahead check

Table 6 Panel B first sorts TIME PERIODS by their current index returns into
low/middle/high terciles. It does not simultaneously sort different coins.

| Next-week conditional index return | Full-sample cutoffs | First-two-year cutoffs |
| --- | ---: | ---: |
| Low state | 1.10% | 0.80% |
| Middle state | 1.21% | 1.44% |
| High state | 8.01% | 6.42% |
| High minus low | 6.91 percentage points | 5.62 percentage points |

The second block uses the first TWO YEARS to determine tercile cutoffs and
examines subsequent out-of-sample sorting. It is an important chronological
threshold check. It is not a documented nested model-selection and sealed final
holdout protocol like the one we intend to use. No evidence that it measures
LightGBM fit, parameter-search uncertainty or our portfolio's transaction costs.

The high and low means occur on DIFFERENT DATES; their difference is not a
simultaneously executable long-short portfolio return. In particular, even the
low-state average next-week return is positive. This table alone cannot justify
shorting whenever the market's previous return is negative. A tradable switching
rule needs its own full time series, cash state, exposure and cost accounting.

For 2+ week forward returns, labels overlap if sampled each week. Authors use
Newey-West with horizon-minus-one lags for the reported predictive/sorting tests.
Our future multi-day labels likewise need matured-label separation at boundaries
and dependence-aware uncertainty, not treatment as independent observations.

## Directional portfolio extension (section 4.2, pp. 2719-2720)

The article also describes a genuinely closer trading construction:

- Candidate sets: largest 3, 5 or 10 coins.
- For each instrument, use the sign of its past THREE-WEEK excess return.
- Positive -> long; negative -> short. Hold ONE WEEK, with no overlapping
  holding sample as described by the authors.
- Main text reports positive unadjusted excess returns and additional information
  after controls for aggregate crypto market and cross-sectional momentum.
  Further three-factor controls weaken results; reported significance differs
  by universe. Detailed tables are in the unreviewed Internet Appendix.

Important replication ambiguity: the paragraph literally says instrument and
MONTH, alongside three-week lookback and one-week holding. This is visually
confirmed in PDF page 33. Main text alone does not fix the exact decision calendar.
Also verify asset selection as-of dates, weighting, excess-return convention,
short feasibility, rebalance/entry timestamps and treatment of missing/delisted
coins. Do not silently assume equal weights or weekly continuous reinvestment.
Reported magnitudes are not verified net-of-fee/slippage/borrow/funding returns.

The first method in section 4.2 finds that aggregate market returns do not
significantly forecast future cross-sectional momentum returns. This is not
proof of zero correlation or independence. The portfolio extension nonetheless
illustrates why two momentum constructions need not be completely redundant.

## Other findings relevant to factor research

- Section 2.3.2/Table 8: Google attention is the current Bitcoin search level
  minus the preceding four-week average, then standardized. Uses similar
  first-two-year tercile cutoff checks. Historical availability/revisions and
  standardization window need replication evidence before live use.
- Section 2.3.4/Tables 10-11: attention correlates with current/recent returns,
  but momentum and attention both remain significant in bivariate prediction.
  Tested interaction terms are not significant. Distinct economic stories or
  significant standalone regressions do not imply independent tradable profits.
  This evidence does not establish a need for nonlinear ML interactions.
- Sections 2.1 and 4.6: distinguish contemporaneous network exposure, returns
  forecasting network growth, and predictive network shocks. Contemporaneous
  factor loading is not itself a usable forecast.
- Section 4.5: volume/volatility ratio is contemporaneously associated with
  returns, but does not forecast future cumulative returns at tested horizons.
  It is NOT our taker-buy/sell imbalance measure; the result neither validates
  nor rejects that candidate.
- Table 12 tests fundamental-to-market VALUATION ratios, not a cross-sectional
  market-cap SIZE premium. Do not use its weak results to dismiss our Size candidate.
- Traditional asset exposure findings apply to the historical sample; they are
  not evidence that crypto is presently market-independent or a universal hedge.

## Project implications: recommendations, not frozen choices

1. Add a SEVEN-DAY forecast/holding candidate with explicit justification, while
   retaining a small set of shorter-horizon alternatives if economically justified.
   This paper cannot decide the winning horizon or rebalance frequency for us.
2. Keep feature lookback, forecast horizon, signal update, trading schedule and
   realized buffer-induced holding duration as separate protocol fields.
3. Separate aggregate timing from cross-sectional ranking and measure market
   exposure. A shared momentum label does not imply the two are interchangeable.
4. Evaluate actual net portfolio returns, funding cashflows, execution delay,
   turnover, risk and inactive-contract handling in our venue/era.
5. Rank-buffer policy remains a separate research component supported by
   Novy-Marx/Velikov, not validated in this paper. A held position may outlive a
   label horizon; any continued hold must follow the predeclared refreshed policy.
6. Fit cutoffs/preprocessing only on permitted historical data; retain our own
   development/validation and sealed final OOS procedure. No OOS performance
   was viewed in reading this historical paper.
7. Keep equal-composite baseline and LightGBM challenger; SHAP is mandatory
   per user, with feature-removal tests. This paper neither studies nor validates
   LightGBM or SHAP-based portfolio selection.

## Specific follow-up material

Priority: the article's Internet Appendix / supplementary material, particularly
section 4.2's directional portfolio results and exact calendar/weighting; Table 6
non-cumulative forecasts and 2014+ robustness; historical index-weight/timestamp
conventions and complete cost assumptions. Do not claim these are verified until
read. Published-article details take precedence over an older working-paper draft.