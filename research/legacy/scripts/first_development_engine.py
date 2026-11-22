"""Nautilus historical execution adapter for Experiment005; conditional proxies."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal

import numpy as np
import pandas as pd
from nautilus_trader.backtest.config import SimulationModuleConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.modules import SimulationModule
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy

HOUR = 3600000
DAY = 86400000
D = Decimal


class HistoricalData:
    def __init__(self, prepared):
        meta = json.loads((prepared / "manifest.json").read_text())
        self.symbols = meta["symbols"]
        self.marks, self.trades, self.funding = {}, {}, {}
        for symbol, group in pd.read_parquet(prepared / "mark.parquet").groupby("instrument_id"):
            group = group.sort_values("bar_open_ms")
            self.marks[symbol] = (group.bar_open_ms.to_numpy(dtype=np.int64) + HOUR,
                                  group.close.to_numpy(dtype=float))
        for symbol, group in pd.read_parquet(prepared / "trade.parquet").groupby("instrument_id"):
            self.trades[symbol] = {int(r.bar_open_ms): (float(r.close), float(r.volume), float(r.quote_volume))
                                   for r in group.itertuples()}
        for symbol, group in pd.read_parquet(prepared / "funding.parquet").groupby("instrument_id"):
            self.funding[symbol] = [(int(r.event_timestamp_ms), float(r.funding_rate))
                                    for r in group.itertuples()]

    def mark(self, symbol, now_ms):
        stamps, values = self.marks[symbol]
        index = int(np.searchsorted(stamps, now_ms, side="right")) - 1
        if index < 0 or now_ms - int(stamps[index]) > 2 * HOUR:
            return None
        return float(values[index]), int(stamps[index])

    def vwap(self, symbol, hour):
        row = self.trades[symbol].get(hour)
        return row[2] / row[1] if row and row[1] > 0 and row[2] > 0 else None

    def events(self, year, end_year=2022):
        if year > end_year:
            raise ValueError("Start year exceeds event calendar end year")
        start = int(datetime(year, 1, 1, tzinfo=UTC).timestamp() * 1000)
        end = int(datetime(end_year, 12, 31, tzinfo=UTC).timestamp() * 1000)
        final = end - HOUR
        events = {}

        def add(symbol, stamp, kind, price, mark_at=None, rate=None):
            key = symbol, stamp
            if key in events:
                old = events[key]
                if rate is not None:
                    old["rate"] = rate
                return
            events[key] = {"symbol": symbol, "stamp": stamp, "kind": kind,
                           "price": price, "mark_at": mark_at, "rate": rate}

        for day in range(start, end + 1, DAY):
            for symbol in self.symbols:
                mark = self.mark(symbol, day)
                if mark:
                    add(symbol, day * 1000000, "mark", *mark)
            add("BTCUSDT", day * 1000000 + 100, "snapshot", self.mark("BTCUSDT", day)[0])
            dt = datetime.fromtimestamp(day / 1000, UTC)
            weekly = dt.weekday() == 0
            initial = day == start
            if weekly or initial:
                for symbol in self.symbols:
                    mark = self.mark(symbol, day + HOUR)
                    if mark:
                        add(symbol, (day + HOUR) * 1000000, "reference", *mark)
                add("BTCUSDT", (day + HOUR) * 1000000 + 100, "decision",
                    self.mark("BTCUSDT", day + HOUR)[0])
                for symbol in self.symbols:
                    price = self.vwap(symbol, day + HOUR)
                    if price:
                        add(symbol, (day + 2 * HOUR) * 1000000, "execution", price)
                add("BTCUSDT", (day + 2 * HOUR) * 1000000 + 100, "check",
                    self.mark("BTCUSDT", day + 2 * HOUR)[0])
        for symbol in self.symbols:
            for stamp, rate in self.funding[symbol]:
                if start <= stamp <= end:
                    mark = self.mark(symbol, stamp)
                    if mark:
                        add(symbol, stamp * 1000000, "funding", *mark, rate=rate)
                    else:
                        # Keep event even without proxy so held exposures fail explicitly.
                        add(symbol, stamp * 1000000, "missing_funding_mark", 1., None, rate)
            price = self.vwap(symbol, final - HOUR)
            if price:
                add(symbol, final * 1000000, "final", price)
        add("BTCUSDT", final * 1000000 + 100, "final_check", self.mark("BTCUSDT", final)[0])
        return [events[k] for k in sorted(events, key=lambda x: (x[1], x[0]))]


class FundingModule(SimulationModule):
    def __init__(self, event_map, by_id):
        super().__init__(SimulationModuleConfig())
        self.events, self.by_id = event_map, by_id
        self.rows, self.pending = [], None

    def pre_process(self, data):
        self.pending = None
        symbol = self.by_id.get(getattr(data, "instrument_id", None))
        event = self.events.get((symbol, data.ts_init))
        if not event or event["rate"] is None:
            return
        quantity = sum((p.quantity.as_decimal() * (1 if p.is_long else -1)
                        for p in self.exchange.cache.positions_open()
                        if p.instrument_id == data.instrument_id), D(0))
        if not quantity:
            return
        if event["mark_at"] is None:
            raise ValueError(f"Held funding event lacks completed mark:{symbol}")
        cash = -quantity * D(str(event["price"])) * D(str(event["rate"]))
        self.pending = {"timestamp_ns": data.ts_init, "instrument_id": symbol,
                        "signed_quantity": str(quantity), "rate": event["rate"],
                        "mark_proxy": event["price"], "mark_available_ms": event["mark_at"],
                        "cashflow_usdt": str(Money(cash, USDT).as_decimal())}

    def process(self, ts_now):
        if self.pending:
            self.exchange.adjust_account(Money(D(self.pending["cashflow_usdt"]), USDT))
            self.rows.append(self.pending)
            self.pending = None

    def log_diagnostics(self, logger):
        pass

    def reset(self):
        self.rows, self.pending = [], None


class Portfolio(Strategy):
    def __init__(self, data, events, instruments, schedule, funding, benchmark=None):
        super().__init__()
        self.data, self.events, self.instruments = data, events, instruments
        self.schedule, self.funding, self.benchmark = schedule, funding, benchmark
        self.marks, self.pending, self.failures = {}, {}, []
        self.fills, self.daily, self.targets, self.closed_pnls = [], [], [], []
        self.previous_fee = self.previous_funding = self.previous_notional = 0.
        self.benchmark_entered = False
        self.by_id = {i.id: s for s, i in instruments.items()}

    def on_start(self):
        for instrument in self.instruments.values():
            self.subscribe_quote_ticks(instrument.id)

    def positions(self):
        return {self.by_id[p.instrument_id]: p for p in self.cache.positions_open()}

    def nav(self, stamp):
        cash = self.cache.account_for_venue(Venue("BINANCE")).balance_total(USDT).as_decimal()
        unrealized, gross, net = 0., 0., 0.
        for symbol, position in self.positions().items():
            mark = self.marks.get(symbol)
            if not mark or stamp // 1000000 - mark[1] > 2 * HOUR:
                self.failures.append(f"Missing/stale held mark:{symbol}:{stamp}")
                continue
            price = self.instruments[symbol].make_price(mark[0])
            unrealized += float(position.unrealized_pnl(price).as_decimal())
            notional = float(position.quantity.as_decimal()) * float(price.as_decimal())
            gross += notional
            net += notional * (1 if position.is_long else -1)
        value = float(cash) + unrealized
        if not np.isfinite(value) or value <= 0:
            self.failures.append(f"Nonpositive NAV:stamp={stamp},cash={cash},unrealized={unrealized},positions={[(s,str(p.quantity),p.is_long) for s,p in self.positions().items()]}")
        return value, gross / value, net / value, float(cash), unrealized

    def on_quote_tick(self, tick):
        symbol = self.by_id[tick.instrument_id]
        event = self.events[(symbol, tick.ts_init)]
        kind, stamp = event["kind"], tick.ts_init
        if event["mark_at"] is not None:
            self.marks[symbol] = event["price"], event["mark_at"]
        day = datetime.fromtimestamp(stamp // 1000000 / 1000, UTC).strftime("%Y-%m-%d")
        if kind == "decision":
            weights = self.schedule.get(day)
            if self.benchmark and not self.benchmark_entered:
                weights = {self.benchmark: 1.0}
                self.benchmark_entered = True
            elif self.benchmark:
                weights = None
            if weights is None:
                return
            nav = self.nav(stamp)[0]
            positions = self.positions()
            for asset in sorted(set(weights) | set(positions)):
                reference = self.data.trades[asset].get((stamp // 1000000 // DAY) * DAY)
                if not reference or reference[0] <= 0:
                    self.failures.append(f"Missing known sizing reference:{asset}:{day}")
                    continue
                quantity = (float(self.instruments[asset].make_qty(abs(weights[asset] * nav / reference[0])).as_decimal())
                            if weights.get(asset, 0.) else 0.)
                quantity *= 1 if weights.get(asset, 0.) >= 0 else -1
                self.pending[asset] = quantity
                self.targets.append({"decision_date": day, "instrument_id": asset,
                                     "weight": weights.get(asset, 0.), "target_quantity": quantity,
                                     "sizing_reference": reference[0], "nav_at_decision": nav})
        elif kind == "execution" and symbol in self.pending:
            target = self.pending.pop(symbol)
            position = self.positions().get(symbol)
            current = float(position.quantity.as_decimal()) * (1 if position.is_long else -1) if position else 0.
            delta = target - current
            if abs(delta) >= 1e-8:
                self.submit_order(self.order_factory.market(
                    self.instruments[symbol].id, OrderSide.BUY if delta > 0 else OrderSide.SELL,
                    self.instruments[symbol].make_qty(abs(delta))))
        elif kind == "final":
            if symbol in self.positions():
                self.close_all_positions(self.instruments[symbol].id)
        elif kind in ("check", "final_check"):
            if self.pending:
                self.failures.append(f"Missing required execution proxies:{self.pending}")
            if kind == "final_check" and self.positions():
                self.failures.append("Final positions not flat")
        elif kind == "snapshot":
            nav, gross, net, cash, unrealized = self.nav(stamp)
            fee = sum(f["commission_usdt"] for f in self.fills)
            carry = sum(float(r["cashflow_usdt"]) for r in self.funding.rows)
            notional = sum(f["notional_usdt"] for f in self.fills)
            self.daily.append({"timestamp": day + "T00:00:00Z", "strategy_nav": nav,
                               "commissions_usdt": fee - self.previous_fee,
                               "funding_cashflow_usdt": carry - self.previous_funding,
                               "traded_notional_usdt": notional - self.previous_notional,
                               "gross_exposure": gross, "net_exposure": net,
                               "cash_usdt": cash, "unrealized_usdt": unrealized})
            self.previous_fee, self.previous_funding, self.previous_notional = fee, carry, notional

    def on_order_filled(self, event):
        price, quantity = float(event.last_px.as_decimal()), float(event.last_qty.as_decimal())
        self.fills.append({"timestamp_ns": event.ts_event,
                           "instrument_id": self.by_id[event.instrument_id],
                           "side": event.order_side.name, "quantity": quantity, "price": price,
                           "commission_usdt": float(event.commission.as_decimal()),
                           "notional_usdt": price * quantity})

    def on_order_rejected(self, event):
        self.failures.append(str(event))

    def on_order_denied(self, event):
        self.failures.append(str(event))

    def on_position_closed(self, event):
        self.closed_pnls.append(float(event.realized_pnl.as_decimal()))


def instrument(symbol):
    values = CryptoPerpetual.to_dict(TestInstrumentProvider.btcusdt_perp_binance())
    values.update(id=str(InstrumentId(Symbol(symbol), Venue("BINANCE"))), raw_symbol=symbol,
                  base_currency=symbol.removesuffix("USDT"),
                  price_precision=8, price_increment="0.00000001", size_precision=8,
                  size_increment="0.00000001", min_quantity="0.00000001", max_quantity=None,
                  min_notional=None, max_notional=None, min_price=None, max_price=None,
                  maker_fee="0.0002", taker_fee="0.0005", margin_init="0.5", margin_maint="0.25",
                  ts_event=0, ts_init=0)
    return CryptoPerpetual.from_dict(values)


def simulate(data, event_list, schedule, output, bps=5, benchmark=None):
    instruments = {s: instrument(s) for s in data.symbols}
    events = {(e["symbol"], e["stamp"]): e for e in event_list}
    by_id = {i.id: s for s, i in instruments.items()}
    funding = FundingModule(events, by_id)
    engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
    engine.add_venue(venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
                     account_type=AccountType.MARGIN, starting_balances=[Money(100000, USDT)],
                     base_currency=USDT, default_leverage=D(2), modules=[funding])
    for item in instruments.values():
        engine.add_instrument(item)
    strategy = Portfolio(data, events, instruments, schedule, funding, benchmark)
    engine.add_strategy(strategy)
    ticks = []
    for event in event_list:
        asset = instruments[event["symbol"]]
        stress = bps / 10000 if event["kind"] in ("execution", "final") else 0
        ticks.append(QuoteTick(asset.id, asset.make_price(event["price"] * (1 - stress)),
                               asset.make_price(event["price"] * (1 + stress)),
                               asset.make_qty(1e8), asset.make_qty(1e8), event["stamp"], event["stamp"]))
    engine.add_data(ticks)
    try:
        engine.run()
        if strategy.failures:
            output.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(strategy.daily).to_csv(output / "INVALID_daily.csv", index=False)
            pd.DataFrame(strategy.fills).to_csv(output / "INVALID_fills.csv", index=False)
            pd.DataFrame(funding.rows).to_csv(output / "INVALID_funding.csv", index=False)
            (output / "failure.json").write_text(json.dumps(strategy.failures[:20], indent=2))
            raise ValueError("Historical simulation invalid:" + repr(strategy.failures[:10]))
        if engine.cache.positions_open():
            raise ValueError("End-of-run positions must be flat")
        cash = float(engine.cache.account_for_venue(Venue("BINANCE")).balance_total(USDT).as_decimal())
        expected = 100000 + sum(strategy.closed_pnls) + sum(float(r["cashflow_usdt"]) for r in funding.rows)
        if abs(cash - expected) > .01 or abs(cash - strategy.daily[-1]["strategy_nav"]) > .01:
            raise ValueError(f"Engine ledger reconciliation failed:{cash},{expected}")
        output.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(strategy.daily).to_csv(output / "engine_daily.csv", index=False)
        pd.DataFrame(strategy.fills).to_csv(output / "fills.csv", index=False)
        pd.DataFrame(funding.rows).to_csv(output / "funding.csv", index=False)
        pd.DataFrame(strategy.targets).to_csv(output / "targets.csv", index=False)
        normalized = {"daily": strategy.daily, "fills": strategy.fills, "funding": funding.rows,
                      "targets": strategy.targets, "closed_pnls": strategy.closed_pnls}
        summary = {"success": True, "ending_nav": cash, "fill_count": len(strategy.fills),
                   "funding_cashflows": len(funding.rows), "slippage_bps": bps,
                   "benchmark": benchmark, "ledger_error_usdt": cash - expected,
                   "financial_sha256": hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()}
        (output / "engine_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        return pd.DataFrame(strategy.daily), summary
    finally:
        engine.dispose()
