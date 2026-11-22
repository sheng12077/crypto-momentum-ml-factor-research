"""Verified hourly stores and continuous event calendar, including terminal guards."""

import json
from datetime import UTC, datetime
import numpy as np
import pandas as pd
from ..settings import DAY, HOUR, START, STOP


class HistoricalData:
    def __init__(self, prepared):
        meta = json.loads((prepared / "manifest.json").read_text())
        self.symbols = meta["symbols"]
        self.marks, self.trades, self.funding = ({}, {}, {})
        for symbol, group in pd.read_parquet(prepared / "mark.parquet").groupby("instrument_id"):
            group = group.sort_values("bar_open_ms")
            self.marks[symbol] = (
                group.bar_open_ms.to_numpy(dtype=np.int64) + HOUR,
                group.close.to_numpy(dtype=float),
            )
        for symbol, group in pd.read_parquet(prepared / "trade.parquet").groupby("instrument_id"):
            self.trades[symbol] = {
                int(r.bar_open_ms): (float(r.close), float(r.volume), float(r.quote_volume))
                for r in group.itertuples()
            }
        for symbol, group in pd.read_parquet(prepared / "funding.parquet").groupby("instrument_id"):
            self.funding[symbol] = [
                (int(r.event_timestamp_ms), float(r.funding_rate)) for r in group.itertuples()
            ]

    def mark(self, symbol, now_ms):
        stamps, values = self.marks[symbol]
        index = int(np.searchsorted(stamps, now_ms, side="right")) - 1
        if index < 0 or now_ms - int(stamps[index]) > 2 * HOUR:
            return None
        return (float(values[index]), int(stamps[index]))

    def vwap(self, symbol, hour):
        row = self.trades[symbol].get(hour)
        return row[2] / row[1] if row and row[1] > 0 and (row[2] > 0) else None


class TerminalHistoricalData(HistoricalData):
    def __init__(self, prepared):
        super().__init__(prepared)
        meta = json.loads((prepared / "manifest.json").read_text())
        self.terminal_ends = {
            s: int(v["effective_ms"]) for s, v in meta.get("terminal_boundaries", {}).items()
        }

    def mark(self, symbol, now_ms):
        end = getattr(self, "terminal_ends", {}).get(symbol)
        if end is not None and now_ms >= end:
            return None
        return super().mark(symbol, now_ms)

    def vwap(self, symbol, hour):
        end = getattr(self, "terminal_ends", {}).get(symbol)
        if end is not None and hour + HOUR > end:
            return None
        return super().vwap(symbol, hour)


class ContinuousData(TerminalHistoricalData):
    def events_range(self, start, last):
        if start < START or last >= STOP or start > last or start % DAY or last % DAY:
            raise ValueError("Event range exceeds continuous reconstruction")
        final = last - HOUR
        events = {}

        def add(symbol, stamp, kind, price, mark_at=None, rate=None):
            key = symbol, stamp
            if key in events:
                if rate is not None:
                    events[key]["rate"] = rate
                    events[key]["funding_price"] = price
                    events[key]["funding_mark_at"] = mark_at
                return
            events[key] = {
                "symbol": symbol,
                "stamp": stamp,
                "kind": kind,
                "price": price,
                "mark_at": mark_at,
                "rate": rate,
                "funding_price": price if rate is not None else None,
                "funding_mark_at": mark_at if rate is not None else None,
            }

        for day in range(start, last + 1, DAY):
            for symbol in self.symbols:
                mark = self.mark(symbol, day)
                if mark:
                    add(symbol, day * 1000000, "mark", *mark)
            anchor = self.mark("BTCUSDT", day)
            if not anchor:
                raise ValueError("Missing BTC snapshot anchor")
            add("BTCUSDT", day * 1000000 + 100, "snapshot", anchor[0])
            if day < last and (
                datetime.fromtimestamp(day / 1000, UTC).weekday() == 0 or day == start
            ):
                for symbol in self.symbols:
                    mark = self.mark(symbol, day + HOUR)
                    if mark:
                        add(symbol, (day + HOUR) * 1000000, "reference", *mark)
                for offset, kind in ((HOUR, "decision"), (2 * HOUR, "check")):
                    anchor = self.mark("BTCUSDT", day + offset)
                    if not anchor:
                        raise ValueError("Missing BTC decision/check anchor")
                    add("BTCUSDT", (day + offset) * 1000000 + 100, kind, anchor[0])
                for symbol in self.symbols:
                    price = self.vwap(symbol, day + HOUR)
                    if price:
                        add(symbol, (day + 2 * HOUR) * 1000000, "execution", price)
        for symbol, end in getattr(self, "terminal_ends", {}).items():
            if symbol in self.symbols and start <= end <= last:
                prior = self.mark(symbol, end - 1)
                add(symbol, end * 1000000 + 50, "terminal_boundary", prior[0] if prior else 1.0)
        for symbol in self.symbols:
            for stamp, rate in self.funding.get(symbol, []):
                if start <= stamp <= last:
                    mark = self.mark(symbol, stamp)
                    if mark:
                        add(symbol, stamp * 1000000, "funding", *mark, rate=rate)
                    else:
                        add(symbol, stamp * 1000000, "missing_funding_mark", 1.0, None, rate)
            price = self.vwap(symbol, final - HOUR)
            if price:
                add(symbol, final * 1000000, "final", price)
        anchor = self.mark("BTCUSDT", final)
        if not anchor:
            raise ValueError("Missing BTC final anchor")
        add("BTCUSDT", final * 1000000 + 100, "final_check", anchor[0])
        return [events[k] for k in sorted(events, key=lambda x: (x[1], x[0]))]
