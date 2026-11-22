"""Typed early observation policy flags and daily diagnostics; no factors or labels."""

from __future__ import annotations

import bisect
import math
from datetime import UTC, datetime

import pyarrow as pa
from build_research_data import HOUR

DAY = 24 * HOUR
START = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
END = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() * 1000)


def flags(symbol, point, finish, policy):
    launch = policy["launches"].get(symbol)
    settlement = policy["settlements"].get(symbol)
    proposed = policy["proposed_launches"].get(symbol)
    return {
        "audit_before_confirmed_launch": launch is not None and point < launch,
        "audit_at_or_after_confirmed_settlement": settlement is not None and point >= settlement,
        "audit_span_crosses_confirmed_boundary": any(
            point < b < finish for b in (launch, settlement) if b is not None
        ),
        "audit_before_proposed_launch": proposed is not None and point < proposed,
        "proposed_launch_not_locally_verified": proposed is not None,
        "known_composite_index": symbol in policy["indices"],
        "lifecycle_origin_unverified": launch is None,
    }


def add_flags(table, symbol, kind, policy):
    n = table.num_rows
    times = table["event_timestamp_ms" if kind == "funding" else "bar_open_ms"].to_pylist()
    reviewed = [flags(symbol, t, t + (1 if kind == "funding" else HOUR), policy) for t in times]
    for key in reviewed[0]:
        table = table.append_column(key, pa.array([row[key] for row in reviewed], pa.bool_()))
    quarantine = [
        r["audit_before_confirmed_launch"]
        or r["audit_at_or_after_confirmed_settlement"]
        or r["audit_span_crosses_confirmed_boundary"]
        or r["audit_before_proposed_launch"]
        for r in reviewed
    ]
    table = table.append_column(
        "quarantine_from_trading_reconstruction", pa.array(quarantine, pa.bool_())
    )
    table = table.append_column("available_at", pa.nulls(n, pa.timestamp("ms", tz="UTC")))
    table = table.append_column("publication_time_proven", pa.array([False] * n, pa.bool_()))
    if kind == "funding":
        # The original normalizer deliberately does not promise payable funding.
        table = table.append_column("funding_payment_proven", pa.array([False] * n, pa.bool_()))
        table = table.append_column("funding_mark_price_raw", pa.nulls(n, pa.string()))
        table = table.append_column("funding_mark_price", pa.nulls(n, pa.float64()))
        table = table.append_column(
            "funding_mark_price_status", pa.array(["absent_in_archive_schema"] * n, pa.string())
        )
        table = table.append_column(
            "funding_interval_source", pa.array(["reported_archive"] * n, pa.string())
        )
    return table


def api_table(rows, meta, policy):
    from build_research_data import normalize_base

    # Null intervals survive the common normalization path as nullable int64.
    raw = pa.table(
        {
            "event_ms": pa.array([str(r["event_timestamp_ms"]) for r in rows], pa.string()),
            "funding_interval_hours": pa.array(
                [
                    str(r["reported_funding_interval_hours"])
                    if r["reported_funding_interval_hours"] is not None
                    else None
                    for r in rows
                ],
                pa.string(),
            ),
            "funding_rate": pa.array([r["funding_rate_raw"] for r in rows], pa.string()),
        }
    )
    record = {
        "symbol": "QTUMUSDT",
        "kind": "funding",
        "sha256": meta["sha256"],
        "source_url": meta["url"],
        "retrieved_at": meta["retrieved_at"],
    }
    table = add_flags(normalize_base(raw, record), "QTUMUSDT", "funding", policy)
    replacements = {
        "source_method": pa.array(["official_rest_history_supplement"] * len(rows), pa.string()),
        "source_recovered": pa.array([True] * len(rows), pa.bool_()),
        "funding_interval_source": pa.array(
            [
                "missing_in_api_response"
                if r["reported_funding_interval_hours"] is None
                else "reported_api"
                for r in rows
            ],
            pa.string(),
        ),
        "funding_mark_price_raw": pa.array([r["mark_price_raw"] for r in rows], pa.string()),
        "funding_mark_price": pa.array(
            [
                float(r["mark_price_raw"]) if r["mark_price_raw"] not in (None, "") else None
                for r in rows
            ],
            pa.float64(),
        ),
        "funding_mark_price_status": pa.array(
            [
                "missing_in_api_response"
                if r["mark_price_raw"] in (None, "")
                else "reported_api_unverified_payment"
                for r in rows
            ],
            pa.string(),
        ),
        "cashflow_validity": pa.array(
            ["unverified_event_price_interval_and_launch"] * len(rows), pa.string()
        ),
    }
    for key, values in replacements.items():
        table = table.set_column(table.schema.get_field_index(key), key, values)
    return table


def daily_rows(symbol, trade, mark, funding, policy):
    funding = sorted(funding, key=lambda row: row["event_timestamp_ms"])
    funding_times = [r["event_timestamp_ms"] for r in funding]
    if len(set(funding_times)) != len(funding_times):
        raise ValueError("duplicate funding events across partitions")
    rows, history, continuous = [], {}, 0
    boundaries = [
        values[symbol] for values in (policy["launches"], policy["settlements"]) if symbol in values
    ]
    for day in range(START, END, DAY):
        reference, last_hour = day + DAY, day + DAY - HOUR
        trades = [trade[t] for t in range(day, reference, HOUR) if t in trade]
        marks = [mark[t] for t in range(day, reference, HOUR) if t in mark]
        close, mark_close = trade.get(last_hour), mark.get(last_hour)
        volume = math.fsum(r["volume"] for r in trades)
        phase = flags(symbol, reference, reference + 1, policy)
        close_phase = flags(symbol, reference - 1, reference, policy)
        close_valid = bool(
            close
            and math.isfinite(close["close"])
            and close["close"] > 0
            and volume > 0
            and not close_phase["audit_before_confirmed_launch"]
            and not close_phase["audit_at_or_after_confirmed_settlement"]
            and not close_phase["audit_before_proposed_launch"]
        )
        continuous = continuous + 1 if close_valid else 0
        history[day] = close_valid
        history = {k: v for k, v in history.items() if k >= day - 120 * DAY}
        blocked_reference = (
            phase["audit_before_confirmed_launch"]
            or phase["audit_at_or_after_confirmed_settlement"]
            or phase["audit_before_proposed_launch"]
        )
        history_ready = continuous >= 121 and not blocked_reference
        partial = any(day < boundary < reference for boundary in boundaries)
        index = bisect.bisect_left(funding_times, reference) - 1
        f = funding[index] if index >= 0 else None
        interval = f["funding_interval_hours"] if f else None
        age = reference - f["event_timestamp_ms"] if f else None
        fresh = bool(
            f
            and interval is not None
            and 0 < age <= interval * HOUR
            and not f["quarantine_from_trading_reconstruction"]
            and not blocked_reference
        )
        rows.append(
            {
                "instrument_id": symbol,
                "data_day": datetime.fromtimestamp(day / 1000, UTC).date().isoformat(),
                "reference_time_ms": reference,
                "trade_hours": len(trades),
                "mark_hours": len(marks),
                "trade_close": close["close"] if close else None,
                "trade_close_raw": close["close_raw"] if close else None,
                "mark_close": mark_close["close"] if mark_close else None,
                "mark_close_raw": mark_close["close_raw"] if mark_close else None,
                "trade_volume_sum": volume if trades else None,
                "trade_quote_volume_sum": math.fsum(r["quote_volume"] for r in trades)
                if trades
                else None,
                "taker_buy_quote_volume_sum": math.fsum(r["taker_buy_quote_volume"] for r in trades)
                if trades
                else None,
                "complete_trade_day": len(trades) == 24,
                "complete_mark_day": len(marks) == 24,
                "valid_closing_observation": close_valid,
                "consecutive_valid_closes": continuous,
                **{
                    f"history_{n}_endpoint_valid": close_valid
                    and history.get(day - n * DAY, False)
                    and not blocked_reference
                    for n in (20, 60, 120)
                },
                "history_121_contiguous_closes": history_ready,
                "partial_confirmed_lifecycle_day": partial,
                "latest_funding_event_ms": f["event_timestamp_ms"] if f else None,
                "latest_funding_rate_raw": f["funding_rate_raw"] if f else None,
                "latest_funding_reported_interval_hours": interval,
                "latest_funding_age_ms": age,
                "latest_funding_quarantined": f["quarantine_from_trading_reconstruction"]
                if f
                else False,
                "funding_freshness_diagnostic": fresh,
                "price_history_diagnostic_candidate": len(trades) == 24
                and len(marks) == 24
                and history_ready
                and not partial
                and not phase["known_composite_index"],
                "historical_size_integrated": False,
                "historical_strategy_eligible": False,
                "publication_time_proven": False,
                **phase,
            }
        )
    return rows


def daily_table(rows):
    strings = {
        "instrument_id",
        "data_day",
        "trade_close_raw",
        "mark_close_raw",
        "latest_funding_rate_raw",
    }
    floats = {
        "trade_close",
        "mark_close",
        "trade_volume_sum",
        "trade_quote_volume_sum",
        "taker_buy_quote_volume_sum",
    }
    integers = {
        "reference_time_ms",
        "trade_hours",
        "mark_hours",
        "consecutive_valid_closes",
        "latest_funding_event_ms",
        "latest_funding_reported_interval_hours",
        "latest_funding_age_ms",
    }
    return pa.table(
        {
            key: pa.array(
                [row[key] for row in rows],
                type=pa.string()
                if key in strings
                else pa.float64()
                if key in floats
                else pa.int64()
                if key in integers
                else pa.bool_(),
            )
            for key in rows[0]
        }
    )
