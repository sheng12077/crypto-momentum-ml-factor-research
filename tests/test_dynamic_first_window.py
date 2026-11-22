"""Chronological labels, stable controls and actual Nautilus risk-exit accounting."""

import numpy as np
import pandas as pd
import pytest

from crypto_factor_research.first_window import score_control, training_rows
from crypto_factor_research.window_data import DAY, HOUR, WindowData, ms


def test_random_scores_do_not_change_when_future_or_other_assets_are_added():
    frame = pd.DataFrame({"instrument_id": ["A", "B"], "feature_cutoff_ms": [0, 0]})
    first = score_control(frame, "random", 1000)
    more = score_control(
        pd.concat(
            [frame, pd.DataFrame({"instrument_id": ["C"], "feature_cutoff_ms": [DAY]})],
            ignore_index=True,
        ),
        "random",
        1000,
    )
    pd.testing.assert_series_equal(first.score, more.score.iloc[:2])


def test_labels_crossing_training_cutoff_never_enter_fit():
    class Data:
        notices = {}

        def vwap(self, symbol, t):
            return 100.0 + t / DAY

    cutoff = ms("2022-01-01")
    frame = pd.DataFrame(
        {"instrument_id": ["A", "A"], "feature_cutoff_ms": [cutoff - 10 * DAY, cutoff - 2 * DAY]}
    )
    rows, rejected = training_rows(frame, Data(), cutoff)
    assert len(rows) == 1 and not rejected
    assert rows.label_available_ms.lt(cutoff).all()


def test_actual_funding_at_scheduled_exit_is_charged_before_closing(tmp_path):
    from momentum_data.backtest.engine import simulate

    start, last = ms("2022-01-03"), ms("2022-01-05")
    stamps = np.arange(start - HOUR, last + HOUR, HOUR, dtype=np.int64)
    bars = pd.DataFrame(
        {
            "instrument_id": "BTCUSDT",
            "bar_open_ms": stamps,
            "open": 100.0,
            "high": 100.0,
            "low": 100.0,
            "close": 100.0,
            "volume": 100.0,
            "quote_volume": 10000.0,
            "taker_buy_volume": 50.0,
            "taker_buy_quote_volume": 5000.0,
        }
    )
    exit_time = start + DAY + 4 * HOUR
    funding = pd.DataFrame(
        {
            "instrument_id": ["BTCUSDT"],
            "event_timestamp_ms": [exit_time],
            "funding_rate": [0.01],
            "funding_interval_hours": [8.0],
        }
    )
    notices = {
        "BTCUSDT": {
            "exit_ms": exit_time,
            "effective_ms": exit_time + HOUR,
            "exit_bar_ms": exit_time - 60000,
            "exit_vwap": 100.0,
        }
    }
    data = WindowData({"trade": bars, "mark": bars, "funding": funding}, notices)
    data.exit_prices["BTCUSDT"] = 100
    events = data.events(start, last, {start})
    collision = next(
        e for e in events if e["symbol"] == "BTCUSDT" and e["stamp"] == exit_time * 1000000
    )
    assert collision["kind"] == "final" and collision["rate"] == 0.01
    folder = tmp_path / "results/lightgbm_5bps"
    daily, result = simulate(data, events, {"2022-01-03": {"BTCUSDT": 0.1}}, folder, bps=5)
    assert result["success"]
    assert daily.strategy_nav.iloc[-1] == pytest.approx(99880, abs=0.01)
    assert result["funding_cashflows"] == 1
    import json

    from crypto_factor_research.window_audit import Oracle, audit_case

    bars.to_parquet(tmp_path / "trade.parquet", index=False)
    bars.to_parquet(tmp_path / "mark.parquet", index=False)
    funding.to_parquet(tmp_path / "funding.parquet", index=False)
    (tmp_path / "notices.json").write_text(json.dumps(notices))
    case = {"case": "lightgbm", "bps": 5}
    assert audit_case(tmp_path, case, Oracle(tmp_path, [case]), start, last)["success"]


def test_independent_position_reconstruction_handles_a_flip_and_partial_close():
    from crypto_factor_research.window_audit import apply_fill

    position = (0.0, 0.0)
    realized = 0.0
    for delta, price in [(2.0, 100.0), (-3.0, 110.0), (0.5, 90.0), (-0.5, 130.0), (1.0, 120.0)]:
        position, pnl = apply_fill(position, delta, price)
        realized += pnl
    assert position == (0.0, 0.0)
    assert realized == pytest.approx(30.0)
