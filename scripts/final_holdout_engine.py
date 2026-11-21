"""Same execution/accounting engine with explicit authorized snapshot boundaries."""
from datetime import UTC, datetime

from final_holdout_common import DAY, HOUR, START, STOP
import hashlib
import json

import pandas as pd
from first_development_engine import (
    AccountType, BacktestEngine, BacktestEngineConfig, D, FundingModule, HistoricalData,
    LoggingConfig, Money, OmsType, Portfolio, QuoteTick, USDT, Venue, instrument,
)


class FinalHistoricalData(HistoricalData):
    def __init__(self, prepared):
        super().__init__(prepared)
        meta = json.loads((prepared / "manifest.json").read_text())
        self.terminal_ends = {s: int(v["effective_ms"]) for s, v in meta.get("terminal_boundaries", {}).items()}

    def mark(self, symbol, now_ms):
        end = getattr(self, "terminal_ends", {}).get(symbol)
        if end is not None and now_ms >= end:
            return None
        return super().mark(symbol, now_ms)

    def vwap(self, symbol, hour):
        end = getattr(self, "terminal_ends", {}).get(symbol)
        if end is not None and hour+HOUR > end:
            return None
        return super().vwap(symbol, hour)

    def events_range(self, start, last):
        if start < START or last >= STOP or start > last or start % DAY or last % DAY:
            raise ValueError("Event range exceeds registered final holdout")
        final = last-HOUR
        events = {}

        def add(symbol, stamp, kind, price, mark_at=None, rate=None):
            key = symbol, stamp
            if key in events:
                if rate is not None:
                    events[key]["rate"] = rate
                return
            events[key] = {"symbol": symbol, "stamp": stamp, "kind": kind,
                           "price": price, "mark_at": mark_at, "rate": rate}

        for day in range(start, last+1, DAY):
            for symbol in self.symbols:
                mark = self.mark(symbol, day)
                if mark:
                    add(symbol, day*1000000, "mark", *mark)
            anchor = self.mark("BTCUSDT", day)
            if not anchor:
                raise ValueError("Missing BTC snapshot anchor")
            add("BTCUSDT", day*1000000+100, "snapshot", anchor[0])
            if day < last and (datetime.fromtimestamp(day/1000, UTC).weekday() == 0 or day == start):
                for symbol in self.symbols:
                    mark = self.mark(symbol, day+HOUR)
                    if mark:
                        add(symbol, (day+HOUR)*1000000, "reference", *mark)
                for offset, kind in ((HOUR, "decision"), (2*HOUR, "check")):
                    anchor = self.mark("BTCUSDT", day+offset)
                    if not anchor:
                        raise ValueError("Missing BTC decision/check anchor")
                    add("BTCUSDT", (day+offset)*1000000+100, kind, anchor[0])
                for symbol in self.symbols:
                    price = self.vwap(symbol, day+HOUR)
                    if price:
                        add(symbol, (day+2*HOUR)*1000000, "execution", price)
        for symbol, end in getattr(self, "terminal_ends", {}).items():
            if symbol in self.symbols and start <= end <= last:
                prior = self.mark(symbol, end-1)
                add(symbol, end*1000000+50, "terminal_boundary", prior[0] if prior else 1.)
        for symbol in self.symbols:
            for stamp, rate in self.funding.get(symbol, []):
                if start <= stamp <= last:
                    mark = self.mark(symbol, stamp)
                    if mark:
                        add(symbol, stamp*1000000, "funding", *mark, rate=rate)
                    else:
                        add(symbol, stamp*1000000, "missing_funding_mark", 1., None, rate)
            price = self.vwap(symbol, final-HOUR)
            if price:
                add(symbol, final*1000000, "final", price)
        anchor = self.mark("BTCUSDT", final)
        if not anchor:
            raise ValueError("Missing BTC final anchor")
        add("BTCUSDT", final*1000000+100, "final_check", anchor[0])
        return [events[k] for k in sorted(events, key=lambda x: (x[1], x[0]))]


class TerminalGuardPortfolio(Portfolio):
    def on_quote_tick(self, tick):
        symbol = self.by_id[tick.instrument_id]
        if self.events[(symbol, tick.ts_init)]["kind"] == "terminal_boundary":
            if symbol in self.positions():
                self.failures.append(f"Unsupported terminal settlement held: {symbol} at {tick.ts_init}; "
                                     "official settlement cashflow required, no synthetic close")
            return
        super().on_quote_tick(tick)


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
    strategy = TerminalGuardPortfolio(data, events, instruments, schedule, funding, benchmark)
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
