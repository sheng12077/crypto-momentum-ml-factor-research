"""Daily technical data gates; never a certified historical trading universe."""

from __future__ import annotations

import bisect
import math
from datetime import UTC, datetime, timedelta

HOUR = 3_600_000
DAY = 24 * HOUR
SIZE_LAG_DAYS = 7
SIZE_VALID_DAYS = 7
REASONS = {
    "trade_day_incomplete": 1,
    "mark_day_incomplete": 2,
    "no_trade_activity": 4,
    "history120_incomplete_or_wrong_episode": 8,
    "funding_missing_or_wrong_episode": 16,
    "funding_outside_last_reported_interval": 32,
    "known_order_stop": 64,
    "partial_lifecycle_day": 128,
    "scoped_execution_block": 256,
    "known_equity_episode": 512,
    "size_missing_or_expired": 1024,
    "size_mapping_missing_ambiguous_or_blocked": 2048,
    "imbalance_inputs_invalid": 4096,
}


def ms(value):
    point = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if point.tzinfo is None:
        raise ValueError("timestamp lacks timezone")
    return int(point.timestamp() * 1000)


def day_text(stamp):
    return datetime.fromtimestamp(stamp / 1000, UTC).strftime("%Y-%m-%d")


def build_events(symbol, ledger, facts, policy):
    launches, stops = set(), set()
    all_events = ledger.get("official_events", [])
    for event in all_events:
        if event["event_type"] == "launch":
            launches.add(ms(event["effective_at"]))
        elif event["event_type"] in ("automatic_settlement", "new_positions_disabled"):
            stops.add(ms(event["effective_at"]))
    record = next((r for r in facts["records"] if r["instrument_id"] == symbol), None)
    equities = []
    if record:
        for episode in record["proposed_episodes"]:
            if episode["effective_from"]:
                launches.add(ms(episode["effective_from"]))
            if episode["effective_to"]:
                stops.add(ms(episode["effective_to"]))
            if episode.get("asset_class") == "equity_derivative" and episode["effective_from"]:
                equities.append(ms(episode["effective_from"]))
    for reset in policy["feature_state_resets"]:
        if reset["instrument_id"] == symbol:
            launches.add(ms(reset["at_utc"]))
    if symbol == "SUNUSDT":
        launches.add(ms(policy["later_SUN_launch"]["at_utc"]))
    return sorted(launches), sorted(stops), sorted(equities)


def epoch_at(stamp, launches):
    return bisect.bisect_right(launches, stamp)


def order_stopped(stamp, launches, stops):
    a, b = bisect.bisect_right(launches, stamp), bisect.bisect_right(stops, stamp)
    return bool(b and (not a or stops[b - 1] >= launches[a - 1]))


def scoped_block(symbol, stamp, scope, policy, legacy_satisfied=False):
    if not ms(policy["research_window_from"]) <= stamp < ms(policy["research_window_to"]):
        return True
    if any(
        r["instrument_id"] == symbol and scope in r["scopes"]
        for r in policy["whole_identifier_exclusions"]
    ):
        return True
    for row in policy["interval_exclusions"]:
        if row["instrument_id"] != symbol or scope not in row["scopes"]:
            continue
        if (
            legacy_satisfied
            and row["reason"] == "verified_legacy_hours_not_integrated_into_existing_release"
        ):
            continue
        if ms(row["from_utc"]) <= stamp < ms(row["to_utc"]):
            return True
    return False


def mapping_at(symbol, stamp, queue, facts, policy, legacy_satisfied=False):
    if scoped_block(symbol, stamp, "size_join", policy, legacy_satisfied):
        return None, "blocked"
    if symbol == "SUNUSDT":
        launch = policy["later_SUN_launch"]
        if stamp < ms(launch["at_utc"]):
            return None, "before_reviewed_SUN_launch"
        return launch["vendor_asset_id"], "reviewed_override_not_join_approved"
    record = next((r for r in facts["records"] if r["instrument_id"] == symbol), None)
    active = []
    if record:
        for episode in record["proposed_episodes"]:
            a, b = episode["effective_from"], episode["effective_to"]
            if a is None and b is None:
                continue  # Unknown starts do not establish an unverified relisting.
            if (a is None or ms(a) <= stamp) and (b is None or stamp < ms(b)):
                active.append(episode)
        if not active:
            return None, "outside_proposed_episode"
    updates = {r["instrument_id"]: r["proposed_vendor_asset_id"] for r in policy["vendor_updates"]}
    updates["1000SATSUSDT"] = policy["sats"]["primary_historical_vendor_asset_id"]
    if symbol in updates:
        return updates[symbol], "reviewed_override_not_join_approved"
    if record:
        ids = {
            e["proposed_vendor_asset_id"]
            for e in active
            if e["proposed_vendor_asset_id"] is not None
        }
    else:
        ids = {r["vendor_asset_id"] for r in queue["candidates_for_manual_review_only"]}
    ids -= {
        r["vendor_asset_id"]
        for r in policy["rejected_vendor_associations"]
        if r["instrument_id"] == symbol
    }
    if len(ids) != 1:
        return None, "missing" if not ids else "ambiguous"
    return next(iter(ids)), "partial_episode_proposal" if record else "literal_unverified"


def size_schedule(rows):
    schedules = {}
    for row in rows:
        day = datetime.strptime(row["snapshot_date"], "%Y%m%d").replace(tzinfo=UTC)
        available = int((day + timedelta(days=1 + SIZE_LAG_DAYS)).timestamp() * 1000)
        item = {
            **row,
            "assumed_available_ms": available,
            "assumed_expires_ms": available + SIZE_VALID_DAYS * DAY,
        }
        schedules.setdefault(row["vendor_asset_id"], []).append(item)
    for items in schedules.values():
        items.sort(key=lambda r: r["assumed_available_ms"])
        if len({r["assumed_available_ms"] for r in items}) != len(items):
            raise ValueError("duplicate vendor/snapshot availability")
    return schedules


def size_at(vendor, stamp, schedules):
    if vendor is None:
        return None
    rows = schedules.get(vendor, [])
    index = bisect.bisect_right([r["assumed_available_ms"] for r in rows], stamp) - 1
    if index < 0 or stamp >= rows[index]["assumed_expires_ms"]:
        return None
    return rows[index]


def merge_hour(target, row):
    stamp = row["bar_open_ms"]
    if stamp % HOUR:
        raise ValueError("non-hourly observation key")
    if stamp in target:
        keys = set(row) - {"source_recovered"}
        if any(target[stamp].get(key) != row[key] for key in keys):
            raise ValueError("conflicting hourly duplicates")
        return False
    target[stamp] = row
    return True


def make_daily(
    symbol,
    start_ms,
    end_ms,
    trade,
    mark,
    funding,
    ledger,
    queue,
    facts,
    policy,
    schedules,
    legacy_satisfied=False,
):
    """Include prior context in start_ms; caller trims output dates afterwards."""
    launches, stops, equities = build_events(symbol, ledger, facts, policy)
    boundaries = sorted(set(launches + stops))
    funding = sorted(funding, key=lambda r: r["event_timestamp_ms"])
    event_times = [r["event_timestamp_ms"] for r in funding]
    if len(event_times) != len(set(event_times)):
        raise ValueError("duplicate funding event timestamp")
    history, run_length, previous_epoch = {}, 0, None
    rows = []
    for day in range(start_ms, end_ms, DAY):
        reference = day + DAY
        current_epoch = epoch_at(reference, launches)
        last_hour = reference - HOUR
        close_epoch = epoch_at(last_hour, launches)
        trade_rows = [trade[t] for t in range(day, reference, HOUR) if t in trade]
        mark_rows = [mark[t] for t in range(day, reference, HOUR) if t in mark]
        tc, mc = trade.get(last_hour), mark.get(last_hour)
        volume = math.fsum(r["volume"] for r in trade_rows)
        zero_activity_constant = bool(
            trade_rows and volume <= 0 and len({r["close"] for r in trade_rows}) == 1
        )
        close_valid = bool(
            tc
            and math.isfinite(tc["close"])
            and tc["close"] > 0
            and volume > 0
            and close_epoch == epoch_at(reference - 1, launches)
            and not order_stopped(reference - 1, launches, stops)
        )
        run_length = (
            run_length + 1 if close_valid and previous_epoch == close_epoch else int(close_valid)
        )
        previous_epoch = close_epoch if close_valid else None
        if close_valid:
            history[day] = close_epoch
        history = {k: v for k, v in history.items() if k >= day - 120 * DAY}
        same_reference_epoch = close_valid and close_epoch == current_epoch
        endpoints = {
            n: bool(same_reference_epoch and history.get(day - n * DAY) == current_epoch)
            for n in (20, 60, 120)
        }
        complete_history = bool(same_reference_epoch and run_length >= 121)
        quote = math.fsum(r["quote_volume"] for r in trade_rows)
        taker = math.fsum(r["taker_buy_quote_volume"] for r in trade_rows)
        imbalance_valid = bool(
            len(trade_rows) == 24
            and quote > 0
            and all(
                0
                <= r["taker_buy_quote_volume"]
                <= r["quote_volume"] + max(1e-12, r["quote_volume"] * 1e-9)
                and 0 <= r["taker_buy_volume"] <= r["volume"] + max(1e-12, r["volume"] * 1e-9)
                for r in trade_rows
            )
        )
        partial = bisect.bisect_left(boundaries, reference) > bisect.bisect_right(boundaries, day)
        stopped = order_stopped(reference, launches, stops)
        execution_block = scoped_block(
            symbol, reference, "regular_execution", policy, legacy_satisfied
        )
        equity_block = bool(equities and reference >= equities[0])
        f_index = bisect.bisect_left(event_times, reference) - 1
        f = funding[f_index] if f_index >= 0 else None
        funding_same = bool(
            f
            and epoch_at(f["event_timestamp_ms"], launches) == current_epoch
            and not order_stopped(f["event_timestamp_ms"], launches, stops)
        )
        age = reference - f["event_timestamp_ms"] if f else None
        f_valid = bool(f and math.isfinite(f["funding_rate"]) and f["funding_interval_hours"] > 0)
        fresh = bool(funding_same and f_valid and age <= f["funding_interval_hours"] * HOUR)
        vendor, mapping_status = mapping_at(
            symbol, reference, queue, facts, policy, legacy_satisfied
        )
        size = size_at(vendor, reference, schedules)
        failures = {
            "trade_day_incomplete": len(trade_rows) != 24,
            "mark_day_incomplete": len(mark_rows) != 24,
            "no_trade_activity": volume <= 0,
            "history120_incomplete_or_wrong_episode": not complete_history,
            "funding_missing_or_wrong_episode": not funding_same or not f_valid,
            "funding_outside_last_reported_interval": not fresh,
            "known_order_stop": stopped,
            "partial_lifecycle_day": partial,
            "scoped_execution_block": execution_block,
            "known_equity_episode": equity_block,
        }
        base_mask = sum(REASONS[key] for key, failed in failures.items() if failed)
        size_mask = base_mask | (REASONS["size_missing_or_expired"] if not size else 0)
        size_mask |= REASONS["size_mapping_missing_ambiguous_or_blocked"] if vendor is None else 0
        size_mask |= REASONS["imbalance_inputs_invalid"] if not imbalance_valid else 0
        class_review = bool(ledger["current_noncoin_annotation"])
        actual_available = size.get("available_at") if size else None
        size_proven = bool(
            size
            and actual_available is not None
            and size["historical_content_version_proven"]
            and ms(actual_available) <= reference
        )
        rows.append(
            {
                "instrument_id": symbol,
                "data_day": day_text(day),
                "reference_time_ms": reference,
                "episode_number": current_epoch,
                "close_episode_number": close_epoch,
                "trade_hours": len(trade_rows),
                "mark_hours": len(mark_rows),
                "trade_close": tc["close"] if tc else None,
                "trade_close_raw": tc["close_raw"] if tc else None,
                "mark_close": mc["close"] if mc else None,
                "trade_volume_sum": volume,
                "trade_quote_volume_sum": quote,
                "taker_buy_quote_volume_sum": taker,
                "recovered_mark_hours": sum(bool(r["source_recovered"]) for r in mark_rows),
                "trade_close_valid_for_history": close_valid,
                "imbalance_inputs_valid": imbalance_valid,
                "zero_activity_constant_day": zero_activity_constant,
                "history20_endpoint_valid": endpoints[20],
                "history60_endpoint_valid": endpoints[60],
                "history120_endpoint_valid": endpoints[120],
                "history120_consecutive_complete": complete_history,
                "consecutive_daily_closes": run_length,
                "partial_lifecycle_day": partial,
                "known_lifecycle_order_block": stopped,
                "scoped_execution_block": execution_block,
                "known_equity_episode": equity_block,
                "funding_event_ms": f["event_timestamp_ms"] if f else None,
                "funding_rate_observed": f["funding_rate"] if f else None,
                "funding_rate_raw": f["funding_rate_raw"] if f else None,
                "funding_interval_hours": f["funding_interval_hours"] if f else None,
                "funding_age_ms": age,
                "funding_same_episode_observed": funding_same,
                "funding_within_reported_interval": fresh,
                "vendor_asset_id": vendor,
                "mapping_status": mapping_status,
                "size_snapshot_date": size["snapshot_date"] if size else None,
                "size_market_cap_decimal": size["market_cap_decimal"] if size else None,
                "size_assumed_available_ms": size["assumed_available_ms"] if size else None,
                "size_assumed_expires_ms": size["assumed_expires_ms"] if size else None,
                "size_publication_and_vintage_proven": size_proven,
                "price_funding_data_candidate": base_mask == 0,
                "four_factor_assumed_size_candidate": size_mask == 0,
                "four_factor_class_review_clear_candidate": size_mask == 0 and not class_review,
                "strict_four_factor_eligible": False,
                "current_asset_class_review_required": class_review,
                "lifecycle_origin_unverified": current_epoch == 0,
                "legacy_BNX_condition_satisfied": legacy_satisfied,
                "base_failure_mask": base_mask,
                "four_factor_failure_mask": size_mask,
            }
        )
    return rows
