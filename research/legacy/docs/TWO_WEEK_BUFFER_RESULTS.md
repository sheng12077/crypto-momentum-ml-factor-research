# Experiment 011 result: retain the two-week no-buffer baseline

## Material Passport

- Registration011:60f29cf; runnable implementationfb4d7ad, merged4d071a7.
- User completed the registered batch. Verification status: VERIFIED (16saved
  cases, two financial replays, unchanged source/model hashes, completed report).
- Independently rechecked saved artifacts in WSL funding-strategy; no new engine
  simulation, model fit or threshold search during this result review.
- Both2022and2023are inspected development years.2024/final OOS remain sealed.

## Supported conclusion

No tested retention buffer improves the no-buffer baseline consistently across
both years under the prespecified gates. supported_retention_ranks=[] is a valid
negative research result, not an execution failure. Keep the two-week entry/exit
rank5baseline as the current development candidate; do not refine thresholds around
the favorable2022rank6result or open another window automatically.

Primary results include original taker fees/funding and5bps extra slippage:

| Retain through rank | 2022 return | Sharpe | MDD | 2023 return | Sharpe | MDD |
|---|---:|---:|---:|---:|---:|---:|
| 5, no buffer | +44.17% | 1.86 | -13.56% | +18.06% | 0.95 | -10.51% |
| 6, width1 | +47.49% | 1.96 | -12.80% | +11.52% | 0.66 | -14.10% |
| 8, width3 | +23.97% | 1.20 | -13.75% | -7.11% | -0.33 | -20.39% |
| 10, width5 | +31.08% | 1.35 | -16.48% | -16.05% | -0.92 | -26.92% |

Rank6passes the single-year primary gate in2022but fails it in2023: return/Sharpe
decline and MDD worsens. Rank8/10reduce turnover but lose money in2023, with larger
drawdowns. At10bps,2023returns are +15.72/+9.43/-8.77/-17.44% for ranks5/6/8/10.
The cost-stress comparison does not rescue the wider buffers.

## Turnover tradeoff

| Retention rank | 2022 notional / control | 2023 notional / control |
|---|---:|---:|
| 6 | 98.31% | 93.48% |
| 8 | 76.92% | 78.72% |
| 10 | 69.81% | 68.49% |

In2023rank8saves about500USDT in commissions versus control, but net profit falls
by about25174USDT; rank10saves about740USDT in commissions but net profit falls by
about34116USDT. Reduced commissions do not offset the changed portfolio performance.
Mark-price and funding paths also differ. Keeping weakening names is a plausible
explanation, not an identified causal mechanism without position-level attribution.

This finding is specific to the fixed models, two-week phase, cohort and thresholds.
It does not establish that every buffer design is ineffective or that another
unregistered parameter would succeed. All tested sizes/results remain visible.

## Completion evidence and artifacts

- completed_cases16/16; cached_controls4; new_historical_simulations12;
  verified_replays2; new_model_fits0; source models unchanged.
- Worker and report both success=true. Four English notebook cells executed.
- WSL read-only verify_results() independently passes all16case checkpoints,
  source/code/runtime hashes, scheduled weights/trades, NAV/cash/fees/funding
  ledgers and financial replays. No historical backtest was rerun in this review.
- Rank-sensitivity chart visually checked. Existing user notebook outputs preserved.
- Original conditional identity/cohort, fractional lots, hourly VWAP/funding proxy,
  unvalidated historical filters/liquidation and reference-fee caveats still apply.

Notebook:notebooks/two_week_buffer_sensitivity.ipynb.
Summary/verification:data/interim/buffer_sensitivity/v20261121_001/results/
{summary,verification}.json. Detailed primary/all-case/monthly/pairwise tables are
under reports/tables/buffer_sensitivity/. Figures are under
reports/figures/buffer_sensitivity/. Completed full-run log:
reports/acquisition/buffer_sensitivity_all_20261121_221855_230661.log.

Next boundary: discuss freezing the no-buffer two-week specification for a new
validation window or a separately registered robustness question. No more buffer
search, new factor, paper/live action or2024/final-OOS inspection occurred here.
