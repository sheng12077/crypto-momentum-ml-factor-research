# Nautilus accounting runtime

This segment executes actual Nautilus orders/fills/positions/accounts on synthetic
quotes. It does not compute learned-strategy performance or read historical/OOS
market data. Registration: experiments/002_nautilus_runtime_accounting.md,
main commit57a15f6. Runtime: CPython3.13.18, stable NautilusTrader1.231.0 on WSL
Ubuntu24.04. Resolved packages are pinned in requirements/nautilus-linux-py313.lock.
The borrowed funding-strategy conda environment is unchanged.

From the project directory in WSL, reproduce the isolated runtime if necessary:

```bash
uv venv --python 3.13 data/interim/runtime/nautilus313
uv pip install --python data/interim/runtime/nautilus313/bin/python \
  -r requirements/nautilus-linux-py313.lock
```

Run the small accounting backtests (seconds, no download):

```bash
data/interim/runtime/nautilus313/bin/python scripts/run_nautilus_smoke.py
data/interim/runtime/nautilus313/bin/python -m pytest -q tests/test_nautilus_smoke.py
```

Summary: data/interim/nautilus_smoke/v20261120_001/summary.json. Success requires
15scenarios, all passed, repeat_runs_identical=true. The report includes normalized
fill sides/quantities/prices/commissions, final balances, cashflows and hashes.
The runtime's pandas deprecation warnings are upstream, not accounting failures.

## Supported conclusion

- Buy1BTCat10000,sell10100: net89.95USDT with5+5.05USDTtakerfees.
- Flat10000roundtrip: net-10USDT. Both commissions charged on actual notional.
- Explicit synthetic bid/ask at0/2/5/10bpsperfill produces monotonically lower
  proceeds; the engine's fills incorporate slippage without another cash debit.
  Prices obey the fixture instrument's0.1tick. This is not an estimated market
  impact model or a historical bid/ask reconstruction.
- Fee profile overrides test-kit defaults: maker0.0002/taker0.0005,noBNB.
  Market orders exercise takerfees only. Maker execution is not validated here.
  Rates are research references, not verified account/historical schedules.
- Stable1.231.0has FundingRateUpdate data but its exchange source has no native
  perpetual funding settlement path. The synthetic ScheduledFunding fixture uses
  SimulationModule.pre_process/process and exchange.adjust_account, the same
  extension used by the package's FX rollover module. This is not a claim of
  native funding support. Positive rate debits long/credits short; negative rate
  reverses sign; flat pays zero. Exact events and+1msjitter are both exercised.
- Funding snapshots holdings before same-timestamp strategy orders. Entry exactly
  at the fixture boundary pays zero; exit there still pays. This is an explicit
  fixture convention, not verified Binance ordering. A missing exact event fails
  rather than charging the later position. Real historical replay must insert
  exact settlement events and resolve simultaneous-fill ordering independently.

## Remaining work before strategy performance

1. Verify2021–2022identity/universe and connect2020warmup without silently
   extending the2020identity release's evidence scope.
2. Implement historical funding/mark and execution adapters. Archive funding
   often lacks settlement mark prices; a declared proxy is not an audited cashflow.
   Weekly01–02UTC VWAP remains an execution assumption requiring an adapter;
   these synthetic quotes do not validate it.
3. Freeze executable features, model/refit rules, holdings, costs and selection
   criteria. First components remain momentum/funding/aggressive imbalance;
   Size deferred. Full LightGBM/SHAP experiments are not implemented by this runner.

Official references: [installation](https://nautilustrader.io/docs/latest/getting_started/installation/),
[quickstart](https://nautilustrader.io/docs/latest/getting_started/quickstart/),
[stable package](https://pypi.org/project/nautilus_trader/1.231.0/).
Latest documentation may describe incompatible2.xAPIs; inspect the pinned stable
package's engine.pyx/modules.pyx when implementing extensions.
