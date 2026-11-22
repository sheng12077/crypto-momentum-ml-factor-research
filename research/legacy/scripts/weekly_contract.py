"""Fixed weekly temporal permissions; no prices, labels or strategy performance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

COUNTS = (
    "price_funding_data_candidate",
    "four_factor_assumed_size_candidate",
    "four_factor_class_review_clear_candidate",
    "strict_four_factor_eligible",
)


def utc(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        if len(text) != 10:
            raise ValueError("timestamp requires timezone")
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def millis(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return int(value.timestamp() * 1000)


def validate_contract(config: dict) -> None:
    fixed = {
        "schema": 1,
        "experiment": "001",
        "stage": "development_calendar_and_coverage_only",
        "timezone": "UTC",
        "weekday": 0,
        "feature_cutoff_hour": 0,
        "decision_hour": 1,
        "execution_window_hours": 1,
        "horizon_days": 7,
        "label_publication_lag_hours": 1,
        "execution_proxy": "following_hour_quote_volume_divided_by_base_volume",
        "target": "simple_forward_execution_proxy_price_return_before_costs_and_funding",
        "development_start": "2021-01-01",
        "sealed_oos_start": "2025-01-01",
        "sealed_oos_end": "2026-11-01",
        "coverage_diagnostic_minimum_names": 20,
        "coverage_threshold_is_trading_approval": False,
        "oos_access_enabled": False,
        "performance_enabled": False,
    }
    for key, expected in fixed.items():
        if type(config.get(key)) is not type(expected) or config[key] != expected:
            raise ValueError("registered contract mismatch: " + key)
    rounds = [
        {
            "name": f"round_{number}",
            "train_start": "2021-01-01",
            "train_end": f"{year}-01-01",
            "validation_start": f"{year}-01-01",
            "validation_end": f"{year + 1}-01-01",
        }
        for number, year in enumerate((2023, 2024), 1)
    ]
    if config.get("rounds") != rounds:
        raise ValueError("approved split mismatch")


def permitted(assignment: datetime, available: datetime, start: str, end: str) -> str:
    if assignment.tzinfo is None or available.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    if not utc(start) <= assignment < utc(end):
        return "outside_window"
    return "usable_by_time_only" if available < utc(end) else "purged_label_boundary"


def weekly_calendar(config: dict) -> list[dict]:
    validate_contract(config)
    cursor, end = utc(config["development_start"]), utc(config["sealed_oos_start"])
    cursor += timedelta(days=(config["weekday"] - cursor.weekday()) % 7)
    rows = []
    while cursor < end:
        decision = cursor + timedelta(hours=config["decision_hour"])
        entry_end = decision + timedelta(hours=config["execution_window_hours"])
        exit_start = decision + timedelta(days=config["horizon_days"])
        exit_end = exit_start + timedelta(hours=config["execution_window_hours"])
        available = exit_end + timedelta(hours=config["label_publication_lag_hours"])
        row = {
            "decision_date": cursor.date().isoformat(),
            "feature_data_day": (cursor - timedelta(days=1)).date().isoformat(),
            "feature_cutoff_ms": millis(cursor),
            "decision_ms": millis(decision),
            "entry_window_start_ms": millis(decision),
            "entry_window_end_ms": millis(entry_end),
            "exit_window_start_ms": millis(exit_start),
            "exit_window_end_ms": millis(exit_end),
            "label_assumed_available_ms": millis(available),
            "label_value_computed": False,
        }
        for split in config["rounds"]:
            for purpose in ("train", "validation"):
                row[f"{split['name']}_{purpose}"] = permitted(
                    decision, available, split[f"{purpose}_start"], split[f"{purpose}_end"]
                )
        rows.append(row)
        cursor += timedelta(days=7)
    if len(rows) != 209:
        raise ValueError("registered calendar must have209 decisions")
    return rows


def weekly_flags(rows: list[dict], calendar: list[dict], config: dict) -> list[dict]:
    """Validate one projected development table and retain scheduled boolean flags."""
    lookup = {}
    start, end = millis(utc(config["development_start"])), millis(utc(config["sealed_oos_start"]))
    expected = {r["feature_cutoff_ms"]: r for r in calendar}
    for row in rows:
        reference = row["reference_time_ms"]
        if not start <= reference < end:
            raise ValueError("coverage row outside development; OOS guard")
        if reference not in expected:
            continue
        if reference in lookup:
            raise ValueError("duplicate decision reference")
        if row["data_day"] != expected[reference]["feature_data_day"]:
            raise ValueError("data day/reference mismatch")
        if any(type(row[key]) is not bool for key in COUNTS):
            raise ValueError("candidate flags must be non-null booleans")
        lookup[reference] = {key: row[key] for key in COUNTS}
    if set(lookup) != set(expected):
        raise ValueError("missing weekly decision row; never silently fill")
    return [
        {"decision_date": row["decision_date"], **lookup[row["feature_cutoff_ms"]]}
        for row in calendar
    ]
