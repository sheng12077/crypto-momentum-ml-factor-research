"""Past-only numeric diagnostics; never an approved trading-universe policy."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta

DAY_MS = 86_400_000
EARLY_END = date(2021, 1, 1)


def normalized(row, early=False):
    day = date.fromisoformat(row["data_day"])
    expected = int(datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC)
                   .timestamp() * 1000)
    if row["reference_time_ms"] != expected:
        raise ValueError("Daily availability reference does not match day+1 midnight")
    close = row["trade_close"]
    valid = bool(close is not None and math.isfinite(close) and close > 0)
    if early:
        blocked = any(row[k] for k in (
            "partial_confirmed_lifecycle_day", "audit_before_confirmed_launch",
            "audit_at_or_after_confirmed_settlement", "audit_span_crosses_confirmed_boundary",
            "audit_before_proposed_launch", "known_composite_index",
        ))
        valid &= bool(row["valid_closing_observation"] and not blocked)
        episode = "early-unverified"
        quote, buy = row["trade_quote_volume_sum"], row["taker_buy_quote_volume_sum"]
        imbalance = bool(row["complete_trade_day"] and quote is not None and buy is not None
                         and math.isfinite(quote) and math.isfinite(buy) and quote > 0
                         and 0 <= buy <= quote + max(1e-12, quote * 1e-9))
    else:
        valid &= bool(row["trade_close_valid_for_history"] and not row["partial_lifecycle_day"]
                      and not row["known_lifecycle_order_block"]
                      and not row["scoped_execution_block"] and not row["known_equity_episode"]
                      and row["episode_number"] == row["close_episode_number"])
        episode = f"development:{row['close_episode_number']}"
        imbalance = bool(row["imbalance_inputs_valid"])
    return {"day": day, "valid": valid, "episode": episode, "imbalance": imbalance,
            "early": early}


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
        bridge = bool(previous and previous["early"] and not row["early"]
                      and day == EARLY_END and consecutive)
        same = previous and previous["episode"] == row["episode"]
        run = run + 1 if row["valid"] and consecutive and (same or bridge) else int(row["valid"])
        result[day] = run
        previous = row
    return result


def seven_day_imbalance(day, rows):
    return all((item := rows.get(day - timedelta(days=i))) and item["imbalance"]
               for i in range(7))


def mapping_covers_window(mapping, day):
    if not mapping:
        return False
    start, end = mapping.get("scope_from"), mapping.get("scope_to_exclusive")
    if not start or not end:
        return False
    start = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end.replace("Z", "+00:00"))
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Identity scope requires timezone-aware timestamps")
    a = datetime.combine(day - timedelta(days=120), datetime.min.time(), UTC)
    b = datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC)
    return bool(start <= a and end >= b and mapping.get("size_identity_join_allowed")
                and mapping.get("price_or_history_splice_allowed"))


def mondays():
    start, stop = date(2021, 1, 4), date(2023, 1, 1)
    result = []
    while start < stop:
        result.append(start)
        start += timedelta(days=7)
    assert len(result) == 104
    return result
