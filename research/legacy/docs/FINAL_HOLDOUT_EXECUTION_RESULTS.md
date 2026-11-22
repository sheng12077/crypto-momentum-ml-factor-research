# Final holdout: real execution, known limits and verified outputs

The user asked for a complete real-data run after repeated handoff failures. The
agent executed v003 prepare/spot/simulation/report through the English notebook.
This run is complete as an execution/availability audit, but the registered
12financial-case experiment is data-incomplete:8valid cases and4blocked cases.
Do not call all market data complete or all twelve financial cases verified.

## Verified strategy results at primary extra slippage5bps

| Window | Net cumulative return | Sharpe rf0 | MDD |
|---|---:|---:|---:|
| Standalone2025 | +30.6057% | 1.4332 | -17.0419% |
| Standalone2026Jan--Oct | -10.5874% | -0.1928 | -24.7852% |
| Continuous2025--2026Oct | +16.3131% | 0.4355 | -24.7852% |

Continuous CAGR8.6075% differs from its cumulative16.3131%. Same frozen rules,
37conditional identifiers,2week,no-buffer,EQ5L/5S,5bps taker/noBNB. Both5/10bps
cases and primary replay are complete for each ML window. Momentum60's2026partial
cases also complete (5bpsreturn-33.4187%,Sharpe-1.1355,MDD-38.1736%). Prior2024
failed validation remains visible;2025profit does not erase2024or2026losses.
No paper/live promotion or strategy alteration is supported by this repair.

Calendars retain the registered partial-last-day convention:365/304/669NAV
snapshots and364/303/668returns; last valuation2025Dec31 00UTC or2026Oct31 00UTC.
Continuous positions/NAV remain across year-end; it is not chained fresh-cash
annual returns.2026values are partial-period cumulative returns.

## Root cause: event semantics, not missing KAVA files

All KAVA funding timestamps have source completed marks within the frozen
freshness limit. A funding timestamp coinciding with an execution quote merged
into that quote and retained rate but lost mark_at. Execution VWAP also cannot
substitute for the funding mark price. The old mapper had7collisions in4symbols:
XTZ1,KAVA4,ONT1,IOST1. Separate funding_price/funding_mark_at fields now survive
merges. The dedicated funding module uses position before same-time fills and
actual completed mark; it still rejects missing/stale/future marks.

Synthetic tests deliberately give execution price200and funding mark110to verify
these are not conflated. Fresh-entry funding is not charged before a position
exists. Noncollision cases retain exact original financial hashes.

## Actual remaining data limitation

The unchanged momentum60control holds EOSUSDT at the2025-05-21 09UTC automatic
settlement (last decision2025-05-12,target10%NAV). The ML portfolio does not hold
EOSat that boundary. Missing verified terminal settlement price/cashflow blocks
momentum60in2025andcontinuous,at both5/10bps:fourplanned cases,all recorded.
The asset was not deleted or closed at a made-up last-price proxy.

Official EOS event:
https://www.binance.com/en/support/announcement/detail/1e89a9ca957c4b0ca7502e60b993e201
Official settlement calculation update (effective2024-11-11):
https://www.binance.com/en/support/announcement/detail/4bcabddf0e81423ebca242e185bf157d
Binance specifies average per-second price index over30minutes (1800points), so
hourly OHLC alone does not prove the exact settlement cashflow. A documented
quarterly delivery-price endpoint probe for EOSUSDT returned[]; no verified exact
terminal price was obtained. Probe response/provenance is preserved under
reports/acquisition/eos_terminal_settlement_probe_20261122/.

Blocked-case comparison gates are null/unavailable. Original full12case acceptance
is not met. This explicit blocked result is not a strategy variant or an excuse
to remove an unfavorable asset. All twelve planned statuses are in case_status.json.

## End-to-end and independent accounting checks

- Real8cases and3primaryMLreplays passed; report_verified=true;4notebook cells ran.
-36synthetic/regression tests passed.
- Independent audit verified3772fills and105958funding rows across all8cases:
  original source VWAP/adverse fills,5bps fees,pre-fill signed quantities,
  completed source marks/availability and rounded funding cashflows.
- Exact trained-model/input/prediction cache hashes match v002;0newmodel fits.
- Original failed versions/contracts remain;v003migration verifies parent contract
  a58f4792bfc835bd935fb0a70fd89b05b83d13d0e1106902891034d3895ee674.
- Continuous dashboard inspected; no fake results shown for blocked controls.

Outputs:data/interim/final_holdout/v20261122_003/results/summary.json,
verification.json,case_status.json,report_complete.json;
reports/acquisition/final_holdout_execution_audit_20261122.json;
reports/acquisition/final_holdout_results_executed.ipynb;
reports/{tables,figures}/final_holdout/.

Original lifecycle publication vintage,retrospective cohort,hourly execution,
funding observability and historical margin/liquidation assumptions remain
conditional. Final2025--2026holdout is now consumed; later tuning cannot reuse it
as independent final validation. No unrequested research or deployment was run.
