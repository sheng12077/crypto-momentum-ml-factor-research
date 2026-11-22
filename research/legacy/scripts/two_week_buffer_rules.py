"""Experiment011: fixed entry5 and retention5/6/8/10, checked every two weeks."""

from strategy_adjustment_rules import mondays

RETENTION_RANKS = (5, 6, 8, 10)


def retain_side(order, previous, rank):
    retained = [symbol for symbol in order[:rank] if symbol in previous][:5]
    incoming = [symbol for symbol in order[:5] if symbol not in retained]
    return retained + incoming[:5-len(retained)]


def schedule(frame, year, rank):
    if rank not in RETENTION_RANKS:
        raise ValueError("Unregistered retention rank; use5/6/8/10")
    if frame.duplicated(["decision_date", "instrument_id"]).any():
        raise ValueError("Duplicate eligible asset/date")
    longs, shorts, weights, audit = [], [], {}, []
    for day in mondays(year)[::2]:
        sample = frame[frame.decision_date == day].sort_values(
            ["score", "instrument_id"], ascending=[False, True], kind="stable")
        old_long, old_short = set(longs), set(shorts)
        if len(sample) < 20:
            longs, shorts = [], []
        else:
            order = sample.instrument_id.tolist()
            longs = retain_side(order, old_long, rank)
            shorts = retain_side(list(reversed(order)), old_short, rank)
        if set(longs) & set(shorts):
            raise ValueError("Overlapping sides")
        weights[day] = {**dict.fromkeys(longs, .1), **dict.fromkeys(shorts, -.1)}
        audit.append({"decision_date": day, "eligible": len(sample), "longs": longs.copy(), "shorts": shorts.copy(),
                      "membership_entries": len(set(longs)-old_long)+len(set(shorts)-old_short),
                      "membership_exits": len(old_long-set(longs))+len(old_short-set(shorts))})
    return weights, audit
