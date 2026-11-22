"""Past-only factor inputs; price/flow data are not gated by unrelated mark bars."""

import numpy as np
import pandas as pd

from .config import DAY, HOUR

FEATURES = ["momentum20", "momentum60", "momentum120", "funding7", "imbalance7"]


def funding_windows(funding, cutoffs):
    """Seven days on observable-time; the lag does not erase hourly-rate coverage."""
    out = np.full(len(cutoffs), np.nan)
    flags = np.zeros(len(cutoffs), dtype=np.int64)
    if funding.empty:
        flags[:] = 1
        return out, flags
    stamps = funding.event_timestamp_ms.to_numpy(dtype=np.int64)
    rates = funding.funding_rate.to_numpy(dtype=float)
    intervals = funding.funding_interval_hours.to_numpy(dtype=float)
    if (np.diff(stamps) <= 0).any():
        raise ValueError("Funding timestamps must be unique and sorted")
    available = stamps + HOUR
    valid = np.isfinite(rates) & np.isfinite(intervals) & (intervals > 0)
    safe_rates = np.where(valid, rates, 0.0)
    safe_intervals = np.where(valid, intervals, 0.0)
    rate_sum = np.r_[0.0, np.cumsum(safe_rates)]
    span_sum = np.r_[0.0, np.cumsum(safe_intervals)]
    invalid = np.r_[0, np.cumsum(~valid)]
    gaps = np.zeros(len(stamps), dtype=np.int64)
    gaps[1:] = np.diff(stamps) > np.maximum(intervals[:-1], intervals[1:]) * HOUR + 1000
    gap_sum = np.r_[0, np.cumsum(gaps)]
    for i, cutoff in enumerate(cutoffs):
        left = int(np.searchsorted(available, cutoff - 7 * DAY, side="left"))
        right = int(np.searchsorted(available, cutoff, side="left"))
        flag = 0
        if right <= left or span_sum[right] - span_sum[left] < 168.0 - 1e-8:
            flag |= 1
        if invalid[right] - invalid[left] or (
            right > left + 1 and gap_sum[right] - gap_sum[left + 1]
        ):
            flag |= 2
        if (
            right <= left
            or not valid[right - 1]
            or cutoff - available[right - 1] > intervals[right - 1] * HOUR + 1000
        ):
            flag |= 4
        if not flag:
            out[i] = rate_sum[right] - rate_sum[left]
        flags[i] = flag
    return out, flags


def price_flow_inputs(frame, funding):
    closes = frame.trade_close.to_numpy(dtype=float)
    epoch = frame.episode_number.to_numpy(dtype=np.int64)
    close_epoch = frame.close_episode_number.to_numpy(dtype=np.int64)
    valid = (
        frame.trade_close_valid_for_history.to_numpy(dtype=bool)
        & np.isfinite(closes)
        & (closes > 0)
        & (epoch == close_epoch)
    )
    length = np.zeros(len(frame), dtype=np.int64)
    segment = np.zeros(len(frame), dtype=np.int64)
    current = 0
    for i in range(len(frame)):
        continuing = bool(i and valid[i] and valid[i - 1] and epoch[i] == epoch[i - 1])
        if valid[i]:
            if not continuing:
                current += 1
            length[i] = length[i - 1] + 1 if continuing else 1
        segment[i] = current
    result = pd.DataFrame(index=frame.index)
    result["history_length"] = length
    result["feature_segment_number"] = segment
    result["close_input_valid"] = valid
    cumulative = np.cumsum(valid)
    result["initial_history_warmup"] = (length < 121) & (cumulative < 121)
    result["history_reset_warmup"] = (length < 121) & (cumulative >= 121)
    for horizon in (20, 60, 120):
        result[f"momentum{horizon}"] = (
            frame.trade_close / frame.trade_close.shift(horizon) - 1
        ).where(length > horizon)
    quote = frame.trade_quote_volume_sum.astype(float)
    buy = frame.taker_buy_quote_volume_sum.astype(float)
    good = (
        frame.imbalance_inputs_valid.astype(bool)
        & frame.trade_hours.eq(24)
        & np.isfinite(quote)
        & np.isfinite(buy)
        & quote.gt(0)
        & buy.ge(0)
        & buy.le(quote + np.maximum(1e-12, quote * 1e-9))
    )
    flow_ready = good.rolling(7, min_periods=7).sum().eq(7)
    denominator = quote.rolling(7, min_periods=7).sum()
    result["imbalance7"] = 2 * buy.rolling(7, min_periods=7).sum() / denominator - 1
    result["flow_inputs_ready"] = flow_ready & denominator.gt(0) & np.isfinite(result.imbalance7)
    cutoff = frame.reference_time_ms.to_numpy(dtype=np.int64)
    result["funding7"], result["funding_window_flags"] = funding_windows(funding, cutoff)
    return result
