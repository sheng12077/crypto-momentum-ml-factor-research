"""Synthetic Nautilus accounting tests. No historical market/OOS inputs are read."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from nautilus_trader.backtest.config import SimulationModuleConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.modules import SimulationModule
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy

ROOT = Path(__file__).resolve().parents[1]
D = Decimal
BASE = 1_609_459_200_000_000_000  # Synthetic timestamp, not historical input.
SECOND = 1_000_000_000


class ScheduledFunding(SimulationModule):
    """Synthetic fixture using the engine's account-adjustment extension.

    NOT an audited Binance adapter. Require a tick at each exact supplied funding
    timestamp, including jitter; never infer or round an 8h boundary. Snapshot
    position before that tick's orders. Explicit mark/rate are settlement facts,
    not feature inputs. Real simultaneous-fill ordering remains unverified.
    """

    def __init__(self, instrument_id, timestamp, rate, mark):
        super().__init__(SimulationModuleConfig())
        self.instrument_id, self.timestamp = instrument_id, timestamp
        self.rate, self.mark = rate, mark
        self.reset()

    def pre_process(self, data):
        if self.done or data.ts_init < self.timestamp:
            return
        if data.ts_init != self.timestamp:
            raise RuntimeError("Skipped funding timestamp: inject an exact event first")
        quantity = D(0)
        for position in self.exchange.cache.positions_open():
            if position.instrument_id == self.instrument_id:
                quantity += position.quantity.as_decimal() * (1 if position.is_long else -1)
        self.pending = -quantity * self.mark * self.rate

    def process(self, ts_now):
        if self.pending is not None and not self.done:
            self.exchange.adjust_account(Money(self.pending, USDT))
            self.cashflows.append(str(self.pending))
            self.done = True

    def log_diagnostics(self, logger):
        pass

    def reset(self):
        self.cashflows, self.done, self.pending = [], False, None


class RoundTrip(Strategy):
    def __init__(self, instrument, direction, entry_ns, exit_ns):
        super().__init__()
        self.instrument, self.direction = instrument, direction
        self.entry_ns, self.exit_ns = entry_ns, exit_ns
        self.entered, self.exited, self.fills = False, False, []

    def on_start(self):
        self.subscribe_quote_ticks(self.instrument.id)

    def on_quote_tick(self, tick):
        if not self.direction:
            return
        if tick.ts_init == self.entry_ns and not self.entered:
            side = OrderSide.BUY if self.direction == 1 else OrderSide.SELL
            self.submit_order(self.order_factory.market(
                self.instrument.id, side, self.instrument.make_qty(1),
            ))
            self.entered = True
        elif tick.ts_init == self.exit_ns and not self.exited:
            self.close_all_positions(self.instrument.id)
            self.exited = True

    def on_order_filled(self, event):
        self.fills.append({
            "side": event.order_side.name, "quantity": str(event.last_qty.as_decimal()),
            "price": str(event.last_px.as_decimal()),
            "commission": str(event.commission.as_decimal()),
            "currency": event.commission.currency.code,
            "liquidity": event.liquidity_side.name, "timestamp_ns": event.ts_event,
        })


def run_case(*, name, exit_anchor="10100", bps=0, direction=1, funding=False,
             jitter_ns=0, entry_boundary=False, exit_boundary=False, rate="0.001",
             omit_funding_tick=False):
    values = CryptoPerpetual.to_dict(TestInstrumentProvider.btcusdt_perp_binance())
    values.update(maker_fee="0.0002", taker_fee="0.0005")
    instrument = CryptoPerpetual.from_dict(values)
    engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
    funding_ns = BASE + 2 * SECOND + jitter_ns
    module = ScheduledFunding(instrument.id, funding_ns, D(rate), D("10000"))
    engine.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
        starting_balances=[Money(100000, USDT)], base_currency=USDT,
        modules=[module] if funding else [],
    )
    engine.add_instrument(instrument)
    entry_ns = funding_ns if entry_boundary else BASE + SECOND
    exit_ns = funding_ns if exit_boundary else BASE + 3 * SECOND
    strategy = RoundTrip(instrument, direction, entry_ns, exit_ns)
    engine.add_strategy(strategy)
    spread = D(bps) / 10000
    ticks = []
    for timestamp in sorted({BASE, BASE + SECOND, funding_ns,
                             BASE + 3 * SECOND, BASE + 4 * SECOND}):
        if omit_funding_tick and timestamp == funding_ns:
            continue
        anchor = D(exit_anchor) if timestamp >= exit_ns else D("10000")
        # Engine consumes adverse bid/ask: no additional slippage cash debit.
        ticks.append(QuoteTick(
            instrument.id, instrument.make_price(anchor * (1 - spread)),
            instrument.make_price(anchor * (1 + spread)),
            instrument.make_qty(100), instrument.make_qty(100), timestamp, timestamp,
        ))
    engine.add_data(ticks)
    try:
        engine.run()
        balance = engine.cache.account_for_venue(Venue("BINANCE")).balance_total(USDT)
        actual, fills = balance.as_decimal() - D(100000), strategy.fills
        assert len(fills) == (2 if direction else 0), (name, fills)
        assert not engine.cache.positions_open(), name
        prices = []
        if direction:
            prices = [
                instrument.make_price(D("10000") * (1 + direction * spread)).as_decimal(),
                instrument.make_price(D(exit_anchor) * (1 - direction * spread)).as_decimal(),
            ]
            sides = ["BUY", "SELL"] if direction == 1 else ["SELL", "BUY"]
            for fill, price, side in zip(fills, prices, sides, strict=True):
                assert D(fill["price"]) == price, (name, fill, price)
                assert fill["side"] == side and D(fill["quantity"]) == 1
                assert fill["liquidity"] == "TAKER" and fill["currency"] == "USDT"
                assert abs(D(fill["commission"]) - price * D("0.0005")) <= D("0.00000001")
        expected_funding = (
            -D(direction) * D("10000") * D(rate) if funding and not entry_boundary else D(0)
        )
        expected = expected_funding
        if direction:
            expected += direction * (prices[1] - prices[0]) - sum(prices) * D("0.0005")
        assert abs(actual - expected) <= D("0.01"), (name, actual, expected)
        if funding:
            assert module.done and len(module.cashflows) == 1, name
            assert D(module.cashflows[0]) == expected_funding, name
        return {
            "name": name, "extra_slippage_bps_per_fill": bps,
            "actual_net_usdt": str(actual), "expected_net_usdt": str(expected),
            "funding_cashflows_usdt": module.cashflows if funding else [],
            "fills": fills, "final_open_positions": 0, "passed": True,
        }
    finally:
        engine.dispose()


def suite():
    cases = [run_case(name="rising_roundtrip"),
             run_case(name="flat_roundtrip", exit_anchor="10000")]
    cases += [run_case(name=f"slippage_{bps}bps", bps=bps) for bps in (0, 2, 5, 10)]
    for jitter in (0, 1_000_000):
        for direction in (1, -1, 0):
            cases.append(run_case(name=f"funding_{direction}_jitter{jitter}", funding=True,
                                  direction=direction, jitter_ns=jitter, exit_anchor="10000"))
    cases += [run_case(name="entry_at_funding", funding=True, entry_boundary=True,
                       exit_anchor="10000"),
              run_case(name="exit_at_funding", funding=True, exit_boundary=True,
                       exit_anchor="10000"),
              run_case(name="negative_funding_long", funding=True, rate="-0.001",
                       exit_anchor="10000")]
    return cases


def main():
    if sys.flags.optimize:
        raise RuntimeError("Assertions are required; do not run this validator with python -O")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/interim/nautilus_smoke/v20261120_001")
    args = parser.parse_args()
    if version("nautilus_trader") != "1.231.0":
        raise RuntimeError("Use pinned NautilusTrader 1.231.0 runtime")
    first, second = suite(), suite()
    assert first == second, "Normalized accounting report is nondeterministic"
    report = {
        "success": True, "scenarios": len(first), "repeat_runs_identical": True,
        "cases_sha256": hashlib.sha256(json.dumps(first, sort_keys=True).encode()).hexdigest(),
        "python": platform.python_version(), "nautilus_trader": version("nautilus_trader"),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(
            (ROOT / "requirements/nautilus-linux-py313.lock").read_bytes()).hexdigest(),
        "synthetic_backtest_executed": True,
        "real_market_strategy_performance_computed": False, "OOS_performance_inspected": False,
        "funding_path": "custom SimulationModule synthetic fixture, not native settlement",
        "real_market_backtest_ready": False,
        "remaining_gates": ["historical funding/mark and execution adapter",
                            "2021-2022 identity/universe and 2020 warmup continuity",
                            "frozen executable features/model/portfolio/selection rules"],
        "cases": first,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}))


if __name__ == "__main__":
    main()
