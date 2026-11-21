"""Frozen Experiment010 rules; no performance-based choices."""

from datetime import date, timedelta

CONFIGS = {
    "A_weekly": {"stage": "reference", "weeks": 1, "buffer": False, "drop": []},
    "B_buffer": {"stage": "execution", "weeks": 1, "buffer": True, "drop": []},
    "C_two_week": {"stage": "execution", "weeks": 2, "buffer": False, "drop": []},
    "D_four_week": {"stage": "execution", "weeks": 4, "buffer": False, "drop": []},
    "E_funding_only": {"stage": "feature", "weeks": 1, "buffer": False, "drop": None},
    "F_no_momentum": {"stage": "feature", "weeks": 1, "buffer": False,
                      "drop": ["momentum20", "momentum60", "momentum120"]},
    "G_no_funding": {"stage": "feature", "weeks": 1, "buffer": False, "drop": ["funding7"]},
    "H_no_imbalance": {"stage": "feature", "weeks": 1, "buffer": False, "drop": ["imbalance7"]},
}


def mondays(year):
    day = date(year, 1, 1)
    day += timedelta(days=(7-day.weekday()) % 7)
    result = []
    while day.year == year:
        result.append(day.isoformat())
        day += timedelta(days=7)
    return result


def training_rows(frame, cutoff):
    return frame[(frame.feature_cutoff_ms < cutoff) & (frame.label_available_ms < cutoff)
                 & frame.label.notna()].reset_index(drop=True).copy()


def buffered_side(order, previous):
    """Best-first order, entry5/retention8, never increase slot count."""
    retain = [symbol for symbol in order[:8] if symbol in previous][:5]
    fill = [symbol for symbol in order[:5] if symbol not in retain]
    return retain + fill[:5-len(retain)]


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
            ["score", "instrument_id"], ascending=[False, True], kind="stable")
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
        result[day] = {**dict.fromkeys(longs, .1), **dict.fromkeys(shorts, -.1)}
        audit.append({"decision_date": day, "eligible": len(sample), "longs": longs.copy(), "shorts": shorts.copy()})
    return result, audit
