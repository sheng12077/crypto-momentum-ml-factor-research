# Frozen 2022 profit attribution

Diagnostic008; post-hoc descriptive evidence, not independent validation. Scope:
original LightGBM validation2022, weekly5long/5short,5bps slippage, fixed actual
fills. No model/strategy changes and no2023/2024/final OOS performance inspection.

## Supported conclusion

June provided23,945.57USDT of the year's22,242.16USDT net profit. Outside June,
net cash PnL was-1,703.41USDT; the other eleven monthly returns compound to-1.50%.
These are different measures: additive cash contributions versus a descriptive
product of monthly returns. Neither is a tradable strategy that skips June.

June's standout result combines large short-side gains with smaller long-side
losses and a profitable long rebound week. Other months often show large opposing
long/short PnL that mostly cancels. Outside June the remaining gross gains were
too small to cover fees and the assumed slippage. This supports profit
concentration and cost sensitivity, not persistent alpha or a causal factor story.

All amounts below are USDT from the100,000USDT initial portfolio. Side contributions
include actual funding and fees; they are not returns on standalone side capital.

| Period | Long net contribution | Short net contribution | Combined |
|---|---:|---:|---:|
| June | -5,949.98 | +29,895.54 | +23,945.57 |
| Full2022 | -46,005.81 | +68,247.97 | +22,242.16 |

Do not infer that removing longs would improve the strategy: doing so changes
market exposure, capital allocation and the economic strategy. Long/short equal
target notionals are not proof of zero beta.

## June timing and assets

Intervals are Monday00:00UTC to next Monday00:00UTC; only June report observations
are included here, so first/last rows are clipped. Monday00:00-to02:00 still holds
the previous week's positions. This attribution is not an alternative fill schedule.

| Holding week starts | Long net | Short net | Total June contribution |
|---|---:|---:|---:|
| May30, June portion | -98.17 | +4,846.27 | +4,748.10 |
| June06 | -10,160.29 | +13,126.45 | +2,966.16 |
| June13 | -4,531.09 | +9,769.28 | +5,238.19 |
| June20 | +13,031.76 | -2,228.98 | +10,802.77 |
| June27, June portion | -4,192.18 | +4,382.53 | +190.35 |

June20 week's net contribution was about45.1% of June profit, and came from the
long side overcoming short losses. Thus, June was not solely a persistent crash
short. This table establishes cash contributions, not why the model selected them.

Largest June asset-level net gains: WAVES+7,026.86,ETC+5,761.47,KAVA+5,650.14,
COMP+4,943.47,ZRX+3,631.82. Largest losses included ATOM-4,224.61 and ALGO-4,122.09.
WAVES/ETC/KAVA have contributions from both position directions during the month;
COMP's gain is long-side. Positive asset contributions can sum to more than net
profit because other assets lose money. Several assets contributed, but this does
not establish independent bets: they may share market/sector exposures.

## Cost decomposition

Fixed actual quantities; price PnL before slippage adds back the known difference
between actual fill and its source hourly VWAP. This is an accounting decomposition,
not a zero-cost resimulation, order-book estimate or arrival-mid slippage estimate.

| Component | June | Other eleven months | Full2022 |
|---|---:|---:|---:|
| Price PnL before assumed slippage | +23,521.05 | +5,508.47 | +29,029.52 |
| Funding | +1,015.18 | +294.91 | +1,310.09 |
| Fees | -295.32 | -3,753.39 | -4,048.72 |
| Assumed slippage cash drag | -295.34 | -3,753.39 | -4,048.73 |
| Net cash PnL | +23,945.57 | -1,703.41 | +22,242.16 |

Outside June, price PnL plus funding was about5,803.38USDT versus7,506.79USDT of
fees/slippage. Some positive gross performance existed, but its margin was small.
June funding helped but was not the main driver. Lower turnover could help costs;
this attribution cannot tell whether slower rebalancing preserves the price gains.

## Verification and reproduction

Run from strategy root:

```text
python scripts/attribute_first_development.py
python -m pytest tests/test_profit_attribution.py -q
```

Runtime used: existing native Python3.11/Pandas/PyArrow/Matplotlib, no Nautilus
rerun required. Five tests pass, including hand-computed long-to-short reversal,
funding/fees/slippage and deliberate NAV corruption rejection. Ruff passes.

Every daily attributed PnL reconciles with original NAV changes: maximum absolute
daily residual4.44e-8USDT, cumulative residual9.11e-8USDT. Recorded funding quantities
agree with fills within5.83e-11 units. Fees/funding/notional match daily ledgers;
fill prices match original5bps-VWAP proxies; month returns match original report;
final positions are flat; all six input files are SHA256 checked before/after.

Outputs, ignored as generated research data:

- data/interim/first_development/v20261121_001/attribution_v001/summary.json
- monthly_components.csv,monthly_side.csv,monthly_asset_side.csv
- weekly_side.csv,june_weekly_side.csv,june_weekly_asset_side.csv
- annual_side.csv,annual_asset_side.csv,june_asset_contributions.csv
- daily_asset_side.csv,daily_reconciliation.csv
- reports/figures/first_development/profit_attribution.png

Month boundaries deliberately match the existing00:00UTC NAV report. A day's
intraday PnL appears at the next snapshot; do not silently compare with civil-day
event-time grouping. Original conditional universe, fractional lots, funding mark
proxies, unvalidated historical filters/liquidation and VWAP execution limits remain.

## Next research decision

First add a matched2022cash-start60day momentum control to test model increment.
Then preregister bounded buffer/cadence comparisons and factor ablations, retain
all outcomes, and freeze the chosen rules before opening2023. June findings alone
do not justify short-only trading, a regime filter or changing selection thresholds.
