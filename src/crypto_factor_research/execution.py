"""Exact filled-quantity adapter for dynamic windows; legacy engine stays frozen."""

import hashlib
import json
from decimal import Decimal

import pandas as pd
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide, PositionAdjustmentType
from nautilus_trader.model.events import PositionAdjusted
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money, Quantity

from momentum_data.backtest.engine import (
    HOUR,
    instrument,
)
from momentum_data.backtest.engine import (
    MarkedFundingModule as BaseFundingModule,
)
from momentum_data.backtest.engine import (
    TerminalGuardPortfolio as BasePortfolio,
)

D = Decimal


class ExactPortfolio(BasePortfolio):
    def __init__(
        self, data, events, instruments, schedule, funding, benchmark=None, exact_execution=True
    ):
        super().__init__(data, events, instruments, schedule, funding, benchmark)
        self.exact_execution = exact_execution
        self.exact_quantities, self.exact_averages = {}, {}
        self.exact_realized_net = D(0)
        self.quantity_normalizations, self.native_sync_pending = [], set()
        self.last_fill_prices = {}
        funding.exact_quantities = self.exact_quantities

    def normalize_native_flat(self, stamp):
        # Only reconcile vendor float bookkeeping when the exact fill ledger is flat.
        for symbol in list(self.native_sync_pending):
            self.native_sync_pending.remove(symbol)
            if self.exact_quantities.get(symbol, D(0)):
                continue
            position = self.positions().get(symbol)
            if position is None:
                continue
            notional = position.quantity.as_decimal() * self.last_fill_prices[symbol]
            if notional > D("0.000001"):
                self.failures.append(f"Native position disagrees with exact flat ledger:{symbol}")
                continue
            residual = D(str(position.signed_qty))
            position.apply_adjustment(
                PositionAdjusted(
                    position.trader_id,
                    position.strategy_id,
                    position.instrument_id,
                    position.id,
                    position.account_id,
                    PositionAdjustmentType.COMMISSION,
                    -residual,
                    None,
                    "Numerical quantity normalization; exact fills flat; no cash adjustment",
                    UUID4(),
                    stamp,
                    stamp,
                )
            )
            self.cache.update_position(position)
            self.quantity_normalizations.append(
                {
                    "timestamp_ns": stamp,
                    "instrument_id": symbol,
                    "native_signed_quantity": str(residual),
                    "exact_signed_quantity": "0",
                    "notional_usdt": str(notional),
                    "cash_adjustment_usdt": "0",
                    "fills_seen": len(self.fills),
                }
            )

    def on_quote_tick(self, tick):
        self.normalize_native_flat(tick.ts_init)
        symbol = self.by_id[tick.instrument_id]
        kind = self.events[(symbol, tick.ts_init)]["kind"]
        if kind == "execution":
            if symbol in self.pending:
                delta = self.pending.pop(symbol) - self.exact_quantities.get(symbol, D(0))
                if abs(delta) >= D("0.00000001"):
                    self.submit_order(
                        self.order_factory.market(
                            self.instruments[symbol].id,
                            OrderSide.BUY if delta > 0 else OrderSide.SELL,
                            Quantity.from_str(format(abs(delta), ".8f")),
                        )
                    )
            return
        if kind == "final":
            current = self.exact_quantities.get(symbol, D(0))
            if current:
                self.submit_order(
                    self.order_factory.market(
                        self.instruments[symbol].id,
                        OrderSide.SELL if current > 0 else OrderSide.BUY,
                        Quantity.from_str(format(abs(current), ".8f")),
                    )
                )
            return
        before = len(self.targets)
        super().on_quote_tick(tick)
        if kind == "decision":
            for target in self.targets[before:]:
                asset, weight = target["instrument_id"], target["weight"]
                quantity = (
                    self.instruments[asset]
                    .make_qty(abs(weight * target["nav_at_decision"] / target["sizing_reference"]))
                    .as_decimal()
                    if weight
                    else D(0)
                )
                quantity *= 1 if weight >= 0 else -1
                self.pending[asset] = quantity
                target["target_quantity"] = str(quantity)

    def on_order_filled(self, event):
        if self.exact_execution:
            symbol = self.by_id[event.instrument_id]
            delta = event.last_qty.as_decimal() * (1 if event.order_side == OrderSide.BUY else -1)
            price_decimal = event.last_px.as_decimal()
            old = self.exact_quantities.get(symbol, D(0))
            average = self.exact_averages.get(symbol, D(0))
            realized = D(0)
            updated = old + delta
            if not old or old * delta > 0:
                average = (abs(old) * average + abs(delta) * price_decimal) / abs(updated)
            else:
                realized = (
                    min(abs(old), abs(delta)) * (price_decimal - average) * (1 if old > 0 else -1)
                )
                if not updated:
                    average = D(0)
                elif updated * old < 0:
                    average = price_decimal
            self.exact_quantities[symbol], self.exact_averages[symbol] = updated, average
            self.exact_realized_net += realized - event.commission.as_decimal()
            self.last_fill_prices[symbol] = price_decimal
            if not updated:
                self.native_sync_pending.add(symbol)
        super().on_order_filled(event)
        self.fills[-1]["quantity"] = str(event.last_qty.as_decimal())


class ExactFundingModule(BaseFundingModule):
    def pre_process(self, data):
        self.pending = None
        symbol = self.by_id.get(getattr(data, "instrument_id", None))
        event = self.events.get((symbol, data.ts_init))
        if not event or event["rate"] is None:
            return
        quantity = sum(
            (
                p.quantity.as_decimal() * (1 if p.is_long else -1)
                for p in self.exchange.cache.positions_open()
                if p.instrument_id == data.instrument_id
            ),
            D(0),
        )
        if hasattr(self, "exact_quantities"):
            quantity = self.exact_quantities.get(symbol, D(0))
        if not quantity:
            return
        mark_at = event.get("funding_mark_at", event["mark_at"])
        price = event.get("funding_price", event["price"])
        now_ms = data.ts_init // 1000000
        if mark_at is None or price is None or not 0 <= now_ms - mark_at <= 2 * HOUR:
            raise ValueError(
                f"Held funding event lacks completed mark:{symbol}:time_ns={data.ts_init}:mark_ms={mark_at}"
            )
        cash = -quantity * D(str(price)) * D(str(event["rate"]))
        self.pending = {
            "timestamp_ns": data.ts_init,
            "instrument_id": symbol,
            "signed_quantity": str(quantity),
            "rate": event["rate"],
            "mark_proxy": price,
            "mark_available_ms": mark_at,
            "cashflow_usdt": str(Money(cash, USDT).as_decimal()),
        }


def simulate(data, event_list, schedule, output, bps=5, benchmark=None, exact_execution=True):
    if not exact_execution:
        raise ValueError("Use the legacy engine explicitly for legacy execution")
    instruments = {s: instrument(s) for s in data.symbols}
    events = {(e["symbol"], e["stamp"]): e for e in event_list}
    by_id = {i.id: s for s, i in instruments.items()}
    funding = ExactFundingModule(events, by_id)
    engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
    engine.add_venue(
        venue=Venue("BINANCE"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        starting_balances=[Money(100000, USDT)],
        base_currency=USDT,
        default_leverage=D(2),
        modules=[funding],
    )
    for item in instruments.values():
        engine.add_instrument(item)
    strategy = ExactPortfolio(
        data, events, instruments, schedule, funding, benchmark, exact_execution
    )
    engine.add_strategy(strategy)
    ticks = []
    for event in event_list:
        asset = instruments[event["symbol"]]
        stress = bps / 10000 if event["kind"] in ("execution", "final") else 0
        ticks.append(
            QuoteTick(
                asset.id,
                asset.make_price(event["price"] * (1 - stress)),
                asset.make_price(event["price"] * (1 + stress)),
                asset.make_qty(1e8),
                asset.make_qty(1e8),
                event["stamp"],
                event["stamp"],
            )
        )
    engine.add_data(ticks)
    try:
        engine.run()
        if exact_execution:
            strategy.normalize_native_flat(event_list[-1]["stamp"])
            if any(strategy.exact_quantities.values()):
                strategy.failures.append("Exact fill-ledger positions not flat")
        if strategy.failures:
            output.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(strategy.daily).to_csv(output / "INVALID_daily.csv", index=False)
            pd.DataFrame(strategy.fills).to_csv(output / "INVALID_fills.csv", index=False)
            pd.DataFrame(funding.rows).to_csv(output / "INVALID_funding.csv", index=False)
            (output / "failure.json").write_text(json.dumps(strategy.failures[:20], indent=2))
            raise ValueError("Historical simulation invalid:" + repr(strategy.failures[:10]))
        if engine.cache.positions_open():
            raise ValueError("End-of-run positions must be flat")
        cash = float(
            engine.cache.account_for_venue(Venue("BINANCE")).balance_total(USDT).as_decimal()
        )
        expected = (
            100000
            + (float(strategy.exact_realized_net) if exact_execution else sum(strategy.closed_pnls))
            + sum(float(r["cashflow_usdt"]) for r in funding.rows)
        )
        if abs(cash - expected) > 0.01 or abs(cash - strategy.daily[-1]["strategy_nav"]) > 0.01:
            output.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(strategy.daily).to_csv(output / "INVALID_daily.csv", index=False)
            pd.DataFrame(strategy.fills).to_csv(output / "INVALID_fills.csv", index=False)
            pd.DataFrame(funding.rows).to_csv(output / "INVALID_funding.csv", index=False)
            raise ValueError(f"Engine ledger reconciliation failed:{cash},{expected}")
        output.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(strategy.daily).to_csv(output / "engine_daily.csv", index=False)
        pd.DataFrame(strategy.fills).to_csv(output / "fills.csv", index=False)
        pd.DataFrame(funding.rows).to_csv(output / "funding.csv", index=False)
        pd.DataFrame(strategy.targets).to_csv(output / "targets.csv", index=False)
        if exact_execution:
            pd.DataFrame(
                strategy.quantity_normalizations,
                columns=[
                    "timestamp_ns",
                    "instrument_id",
                    "native_signed_quantity",
                    "exact_signed_quantity",
                    "notional_usdt",
                    "cash_adjustment_usdt",
                    "fills_seen",
                ],
            ).to_csv(output / "quantity_normalizations.csv", index=False)
        normalized = {
            "daily": strategy.daily,
            "fills": strategy.fills,
            "funding": funding.rows,
            "targets": strategy.targets,
            "closed_pnls": strategy.closed_pnls,
        }
        if exact_execution:
            normalized["quantity_normalizations"] = strategy.quantity_normalizations
        summary = {
            "success": True,
            "ending_nav": cash,
            "fill_count": len(strategy.fills),
            "funding_cashflows": len(funding.rows),
            "slippage_bps": bps,
            "benchmark": benchmark,
            "ledger_error_usdt": cash - expected,
            "financial_sha256": hashlib.sha256(
                json.dumps(normalized, sort_keys=True).encode()
            ).hexdigest(),
        }
        if exact_execution:
            summary["exact_execution"] = True
            summary["native_quantity_normalizations"] = len(strategy.quantity_normalizations)
        (output / "engine_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        return pd.DataFrame(strategy.daily), summary
    finally:
        engine.dispose()
