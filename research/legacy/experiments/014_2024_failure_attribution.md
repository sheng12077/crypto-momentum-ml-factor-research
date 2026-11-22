# Diagnostic 014: frozen 2024 failure attribution

Registered after annual/monthly performance inspection, before detailed side and
asset reconstruction. This is post-hoc descriptive accounting, not a new OOS
strategy test. No revised hypothesis or selection threshold will be passed off
as prespecified performance evidence.

Scope: only saved v002 2024 primary 5bps ML and matched momentum60 daily NAV,
fills, funding, targets, predictions/SHAP, prepared mark/trade inputs; existing
10bps summary and BTC/ETH benchmarks for context. Final2025--2026 remains sealed.
No model fits, historical simulation, new labels, downloads or parameter changes.

Questions: which side, months and assets account for losses? Is loss primarily
price selection, fee drag, recorded funding or adverse fill assumptions? Does
concentration resemble the development-period best-month pattern? All answers
are open: short-side losses, weak longs and excessive costs are hypotheses, not
assumed explanations. SHAP describes predictions, not realized causal profit.

Method: reconstruct additive linear marked PnL from fixed executed quantities
and original completed-hour marks. Split reversal fees by closed/opened quantity;
verify every funding quantity and sum actual funding cashflows. Decompose actual
price PnL into same-quantity source-VWAP price PnL less 5bps fill displacement.
That displacement is an accounting sensitivity, not a zero-cost strategy rerun.
Maintain original midnight-snapshot monthly boundaries. Report both strategies,
all months/sides/assets, worst/best contributors, selected-name feature/SHAP
contrasts, and 7day training target vs14day trading cadence as an untested possible
limitation only. No new signal sorting or adjusted-strategy results.

Acceptance: each daily NAV change and cumulative reconstruction within0.01USDT;
fees/funding/notional match daily ledgers, funding quantities within1e-6, final
flat, finite outputs, all input hashes unchanged. Publish no unreconciled result.
Validate hand-calculated reversal accounting and reject corrupted NAV on a
synthetic fixture before historical reconstruction. Produce CSV/JSON, an English
figure and concise conclusions that distinguish identity from hypothesis.
