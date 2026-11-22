"""Frozen feature definitions and episode-aware trailing history checks."""

import math
from datetime import UTC, date, datetime, timedelta
import numpy as np
import pandas as pd
from ..settings import DAY, HOUR, FEATURES, ms

DAY_MS = DAY
EARLY_END = date(2021, 1, 1)


def normalized(row, early=False):
    day = date.fromisoformat(row["data_day"])
    expected = int(
        datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC).timestamp() * 1000
    )
    if row["reference_time_ms"] != expected:
        raise ValueError("Daily availability reference does not match day+1 midnight")
    close = row["trade_close"]
    valid = bool(close is not None and math.isfinite(close) and close > 0)
    if early:
        blocked = any(
            row[k]
            for k in (
                "partial_confirmed_lifecycle_day",
                "audit_before_confirmed_launch",
                "audit_at_or_after_confirmed_settlement",
                "audit_span_crosses_confirmed_boundary",
                "audit_before_proposed_launch",
                "known_composite_index",
            )
        )
        valid &= bool(row["valid_closing_observation"] and not blocked)
        episode = "early-unverified"
        quote, buy = row["trade_quote_volume_sum"], row["taker_buy_quote_volume_sum"]
        imbalance = bool(
            row["complete_trade_day"]
            and quote is not None
            and buy is not None
            and math.isfinite(quote)
            and math.isfinite(buy)
            and quote > 0
            and 0 <= buy <= quote + max(1e-12, quote * 1e-9)
        )
    else:
        valid &= bool(
            row["trade_close_valid_for_history"]
            and not row["partial_lifecycle_day"]
            and not row["known_lifecycle_order_block"]
            and not row["scoped_execution_block"]
            and not row["known_equity_episode"]
            and row["episode_number"] == row["close_episode_number"]
        )
        episode = f"development:{row['close_episode_number']}"
        imbalance = bool(row["imbalance_inputs_valid"])
    return {"day": day, "valid": valid, "episode": episode, "imbalance": imbalance, "early": early}


def numeric_history(rows):
    """Hypothesize the year bridge only; still reset known episode changes/gaps.

    The early release has a different episode schema. No matching integer IDs or
    price comparisons are used as proof of identity across releases.
    """
    result = {}
    run, previous = 0, None
    for row in rows:
        day = row["day"]
        if day in result or (previous and day <= previous["day"]):
            raise ValueError("Duplicate or unordered daily observations")
        consecutive = bool(previous and day - previous["day"] == timedelta(days=1))
        bridge = bool(
            previous and previous["early"] and not row["early"] and day == EARLY_END and consecutive
        )
        same = previous and previous["episode"] == row["episode"]
        run = run + 1 if row["valid"] and consecutive and (same or bridge) else int(row["valid"])
        result[day] = run
        previous = row
    return result


def funding_feature(events, cutoff):
    selected = [
        r
        for r in events
        if cutoff - 7 * DAY <= r["event_timestamp_ms"] and r["event_timestamp_ms"] + HOUR < cutoff
    ]
    if not selected:
        return None
    intervals = [r["funding_interval_hours"] for r in selected]
    if any(v is None or v <= 0 for v in intervals) or sum(intervals) < 168:
        return None
    last = selected[-1]
    if cutoff - last["event_timestamp_ms"] > last["funding_interval_hours"] * HOUR + 1000:
        return None
    if any(
        b["event_timestamp_ms"] - a["event_timestamp_ms"]
        > max(a["funding_interval_hours"], b["funding_interval_hours"]) * HOUR + 1000
        for a, b in zip(selected, selected[1:], strict=False)
    ):
        return None
    rates = [r["funding_rate"] for r in selected]
    return math.fsum(rates) if all(math.isfinite(v) for v in rates) else None


def features_for_dates(rows, marks, funding, symbol, dates):
    points = [normalized(r) for r in rows]
    history = numeric_history(points)
    normalized_days = {p["day"]: p for p in points}
    by_day = {date.fromisoformat(r["data_day"]): r for r in rows}
    counts = (
        pd.Series([r["bar_open_ms"] // DAY for r in marks], dtype="int64").value_counts().to_dict()
    )
    result = []
    for decision in dates:
        cutoff, day = ms(decision.isoformat()), decision - timedelta(days=1)
        row = by_day.get(day)
        recent = [by_day.get(day - timedelta(days=i)) for i in range(7)]
        valid = all(recent) and all(
            normalized_days[day - timedelta(days=i)]["imbalance"] for i in range(7)
        )
        rate = funding_feature(funding, cutoff)
        if not (
            row
            and history[day] >= 121
            and counts.get((cutoff - DAY) // DAY, 0) == 24
            and valid
            and (row["base_failure_mask"] & ~(8 | 2)) == 0
            and rate is not None
        ):
            continue
        # Match original compensated summation exactly.
        quote = math.fsum(r["trade_quote_volume_sum"] for r in recent)
        buy = math.fsum(r["taker_buy_quote_volume_sum"] for r in recent)
        if quote <= 0:
            continue
        item = {
            "instrument_id": symbol,
            "decision_date": decision.isoformat(),
            "feature_cutoff_ms": cutoff,
            "decision_ms": cutoff + HOUR,
            "label_available_ms": cutoff + 3 * HOUR + 7 * DAY,
            "label": None,
            "funding7": rate,
            "imbalance7": 2 * buy / quote - 1,
        }
        for horizon in (20, 60, 120):
            item[f"momentum{horizon}"] = (
                row["trade_close"] / by_day[day - timedelta(days=horizon)]["trade_close"] - 1
            )
        if not all(np.isfinite(item[k]) for k in FEATURES):
            raise ValueError("Nonfinite feature")
        result.append(item)
    return result
