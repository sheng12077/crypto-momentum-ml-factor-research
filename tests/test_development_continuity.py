import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from development_continuity_rules import (  # noqa: E402
    mapping_covers_window,
    mondays,
    normalized,
    numeric_history,
    seven_day_imbalance,
)


def point(day, valid=True, episode="early-unverified", early=True):
    return {"day": day, "valid": valid, "episode": episode, "early": early, "imbalance": True}


def test_120day_return_requires_121_closes_and_bridge_is_only_numeric():
    start = date(2020, 9, 3)
    rows = [point(start + timedelta(days=i)) for i in range(120)]
    rows.append(point(date(2021, 1, 1), episode="development:0", early=False))
    result = numeric_history(rows)
    assert result[date(2020, 12, 31)] == 120
    assert result[date(2021, 1, 1)] == 121
    assert not mapping_covers_window({
        "scope_from": "2020-01-01T00:00:00Z",
        "scope_to_exclusive": "2021-01-01T00:00:00Z",
        "size_identity_join_allowed": True, "price_or_history_splice_allowed": False,
    }, date(2021, 1, 1))


@pytest.mark.parametrize("failure", ["gap", "invalid_close", "episode_change"])
def test_close_chain_resets(failure):
    start = date(2021, 1, 1)
    rows = [point(start + timedelta(days=i), episode="development:0", early=False)
            for i in range(5)]
    if failure == "gap":
        rows.pop(2)
    elif failure == "invalid_close":
        rows[2]["valid"] = False
    else:
        for row in rows[2:]:
            row["episode"] = "development:1"
    result = numeric_history(rows)
    assert result[start + timedelta(days=4)] == (3 if failure == "episode_change" else 2)


def test_future_rows_cannot_change_prefix_history_or_imbalance():
    start = date(2021, 1, 1)
    rows = [point(start + timedelta(days=i), early=False, episode="development:0")
            for i in range(10)]
    prefix = numeric_history(rows[:7])
    rows[-1]["valid"] = rows[-1]["imbalance"] = False
    full = numeric_history(rows)
    assert all(full[day] == count for day, count in prefix.items())
    assert seven_day_imbalance(start + timedelta(days=6), {r["day"]: r for r in rows})


def test_imbalance_requires_all_seven_days_and_calendar_is_bounded():
    start = date(2021, 1, 1)
    rows = {start + timedelta(days=i): point(start + timedelta(days=i)) for i in range(7)}
    last = start + timedelta(days=6)
    assert seven_day_imbalance(last, rows)
    rows[start]["imbalance"] = False
    assert not seven_day_imbalance(last, rows)
    days = mondays()
    assert len(days) == 104 and days[0] == date(2021, 1, 4) and days[-1] == date(2022, 12, 26)


def test_mismatched_reference_timestamp_is_rejected_before_other_fields():
    with pytest.raises(ValueError, match="reference"):
        normalized({"data_day": "2021-01-01", "reference_time_ms": 0})


def test_scope_needs_full_lookback_and_explicit_splice_permission():
    mapping = {"scope_from": "2020-01-01T00:00:00Z",
               "scope_to_exclusive": "2023-01-01T00:00:00Z",
               "size_identity_join_allowed": True, "price_or_history_splice_allowed": True}
    assert mapping_covers_window(mapping, date(2021, 1, 3))
    mapping["scope_from"] = "2021-01-01T00:00:00Z"
    assert not mapping_covers_window(mapping, date(2021, 1, 3))


def test_duplicate_dates_fail_closed():
    row = point(date(2021, 1, 1))
    with pytest.raises(ValueError, match="Duplicate"):
        numeric_history([row, row])


def test_early_zero_denominator_is_missing_not_neutral():
    day = date(2020, 12, 31)
    row = {"data_day": day.isoformat(), "reference_time_ms": int(
        datetime(2021, 1, 1, tzinfo=UTC).timestamp() * 1000),
        "trade_close": 100, "valid_closing_observation": True,
        "complete_trade_day": True, "trade_quote_volume_sum": 0,
        "taker_buy_quote_volume_sum": 0}
    row.update({key: False for key in (
        "partial_confirmed_lifecycle_day", "audit_before_confirmed_launch",
        "audit_at_or_after_confirmed_settlement", "audit_span_crosses_confirmed_boundary",
        "audit_before_proposed_launch", "known_composite_index")})
    assert not normalized(row, early=True)["imbalance"]
