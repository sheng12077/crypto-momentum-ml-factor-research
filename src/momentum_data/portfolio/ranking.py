"""Frozen two-week cross-sectional ranking; quantities are held between decisions."""

from datetime import date, timedelta


def mondays(year):
    day = date(year, 1, 1)
    day += timedelta(days=(7 - day.weekday()) % 7)
    result = []
    while day.year == year:
        result.append(day.isoformat())
        day += timedelta(days=7)
    return result


def buffered_side(order, previous):
    """Best-first order, entry5/retention8, never increase slot count."""
    retain = [symbol for symbol in order[:8] if symbol in previous][:5]
    fill = [symbol for symbol in order[:5] if symbol not in retain]
    return retain + fill[: 5 - len(retain)]


def portfolio_schedule(frame, year, weeks=1, buffer=False):
    if weeks not in (1, 2, 4) or (buffer and weeks != 1):
        raise ValueError("Unregistered execution configuration")
    result, audit = {}, []
    longs, shorts = [], []
    for index, day in enumerate(mondays(year)):
        if index % weeks:
            # Absence of decision means keep actual quantity in Nautilus.
            continue
        sample = frame[frame.decision_date == day].sort_values(
            ["score", "instrument_id"], ascending=[False, True], kind="stable"
        )
        if len(sample) < 20:
            longs, shorts = [], []
        else:
            order = sample.instrument_id.tolist()
            if buffer:
                longs = buffered_side(order, longs)
                shorts = buffered_side(list(reversed(order)), shorts)
            else:
                longs, shorts = order[:5], order[-5:]
        if set(longs) & set(shorts):
            raise ValueError("Overlapping long/short buffer slots")
        result[day] = {**dict.fromkeys(longs, 0.1), **dict.fromkeys(shorts, -0.1)}
        audit.append(
            {
                "decision_date": day,
                "eligible": len(sample),
                "longs": longs.copy(),
                "shorts": shorts.copy(),
            }
        )
    return result, audit
