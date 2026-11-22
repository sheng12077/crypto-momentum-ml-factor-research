import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_validation_2024 import DAY, END, HOUR, START, append_features, calendar, training_labels
from run_validation_2024 import schedule, training_rows


def test_leap_calendar_two_week_phase_and_engine():
    from first_development_engine import HistoricalData

    assert END-START == 366*DAY
    assert len(calendar()) == 53
    assert calendar()[0] == date(2024, 1, 1) and calendar()[-1] == date(2024, 12, 30)
    names = [f"A{i:02d}" for i in range(20)]
    sample = pd.DataFrame([{"decision_date": d.isoformat(), "instrument_id": s, "score": 1.}
                           for d in calendar() for s in names])
    plan = schedule(sample, "score")
    assert len(plan) == 27 and "2024-01-08" not in plan and "2024-12-30" in plan
    assert plan["2024-01-01"] == {**dict.fromkeys(names[:5], .1), **dict.fromkeys(names[-5:], -.1)}
    data = HistoricalData.__new__(HistoricalData)
    data.symbols, data.funding = ["BTCUSDT"], {"BTCUSDT": []}
    data.mark, data.vwap = lambda s, t: (100., t), lambda s, t: 100.
    events = data.events(2024, end_year=2024)
    assert len([r for r in events if r["kind"] == "snapshot"]) == 366
    final = [r for r in events if r["kind"] == "final"][0]
    assert pd.Timestamp(final["stamp"], tz="UTC") == pd.Timestamp("2024-12-30T23:00Z")


def test_training_labels_preserve_old_values_and_purge_boundary():
    cutoffs = [START-370*DAY, START-14*DAY, START-7*DAY, START]
    frame = pd.DataFrame({"instrument_id": "BTCUSDT", "feature_cutoff_ms": cutoffs,
                          "label_available_ms": [t+7*DAY+3*HOUR for t in cutoffs],
                          "label": [.3, None, None, None]})
    trades = pd.DataFrame({"instrument_id": "BTCUSDT", "bar_open_ms": [cutoffs[1]+HOUR, cutoffs[1]+7*DAY+HOUR],
                           "volume": [2., 4.], "quote_volume": [200., 440.]})
    result = training_labels(frame, trades)
    assert abs(result.loc[1, "label"]-.1) < 1e-12 and result.loc[0, "label"] == .3
    assert result.loc[2:, "label"].isna().all()
    assert list(training_rows(result).index) == [0, 1]
    future = pd.DataFrame({"instrument_id": ["BTCUSDT"], "bar_open_ms": [START+HOUR],
                           "volume": [1.], "quote_volume": [999999.]})
    pd.testing.assert_frame_equal(training_labels(frame, pd.concat([trades, future])), result)


def test_features_are_future_invariant_and_unlabelled():
    rows = []
    for i in range(162):
        day = date(2023, 8, 1)+timedelta(days=i)
        rows.append({"data_day": day.isoformat(), "reference_time_ms": int(pd.Timestamp(
            day+timedelta(days=1), tz="UTC").timestamp()*1000), "trade_close": 100.+i,
            "trade_close_valid_for_history": True, "partial_lifecycle_day": False,
            "known_lifecycle_order_block": False, "scoped_execution_block": False,
            "known_equity_episode": False, "episode_number": 1, "close_episode_number": 1,
            "imbalance_inputs_valid": True, "base_failure_mask": 0,
            "trade_quote_volume_sum": 10., "taker_buy_quote_volume_sum": 6.})
    marks = [{"bar_open_ms": START-DAY+i*HOUR, "close": 100.} for i in range(24)]
    funding = [{"event_timestamp_ms": t, "funding_rate": .0001, "funding_interval_hours": 8}
               for t in range(START-7*DAY, START, 8*HOUR)]
    before = append_features(rows, marks, funding, "BTCUSDT")
    assert len(before) == 1 and before[0]["decision_date"] == "2024-01-01"
    assert before[0]["label"] is None
    for row in rows:
        if row["data_day"] >= "2024-01-01":
            row["trade_close"] = 999999.
    assert append_features(rows, marks, funding, "BTCUSDT") == before
