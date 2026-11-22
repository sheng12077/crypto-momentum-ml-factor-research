# Diagnostic008: frozen 2022 profit concentration

Registered after inspection of annual/monthly results, before detailed attribution.
This is descriptive post-hoc analysis, not an independent strategy test.

Scope: existing results_v003/lightgbm_validation/slippage_5bps fills, funding,
daily equity and prepared_v003 marks only. No new model, simulation, parameter
selection, downloads, or 2023/2024/final OOS inspection.

Questions: is June profit concentrated in particular weeks/assets/sides? Does
funding or fee drag explain the other months? Hypotheses include short-side
crash exposure and concentrated relative-performance trades; neither is assumed
true. Evaluate all months and both sides, retaining unfavorable contributions.

Method: reconstruct linear marked price PnL from actual fixed fills and completed
hour marks at original daily snapshots; assign price changes to the sign of the
position held over each segment. Split reversal fees by closed/opened quantity.
Use actual recorded funding cashflows and reconcile their signed quantities.
This is ledger attribution, not a replacement execution/backtest engine.

Acceptance: every daily equity change reconciles within 0.01 USDT, cumulative
equity within 0.01 USDT, all fees/funding accounted, final positions flat, and
input hashes unchanged. Fail rather than publish unreconciled attribution.
Report monthly/weekly/asset/side cash PnL, top contributors, concentration and
fee/funding decomposition. Excluding June is a descriptive sensitivity only,
never a tradable rule or a reason to change registered thresholds.

Do not interpret SHAP as realized PnL or use one-year beta estimates as causal
proof. Historical universe/execution limitations of005 remain in force.
