"""Same execution/accounting engine with explicit authorized snapshot boundaries."""
from datetime import UTC, datetime

from final_holdout_common import DAY, HOUR, START, STOP
from first_development_engine import HistoricalData


class FinalHistoricalData(HistoricalData):
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
