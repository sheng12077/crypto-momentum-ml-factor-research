import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_validation_2023 import DAY, HOUR, START, append_features, calendar  # noqa: E402


def test_2023_calendar_is_fixed_and_sealed():
    assert len(calendar()) == 52
    assert calendar()[0] == date(2023, 1, 2)
    assert calendar()[-1] == date(2023, 12, 25)
    assert all(d.year == 2023 and d.weekday() == 0 for d in calendar())


def test_features_only_use_prior_days_and_do_not_compute_labels():
    rows = []
    for i in range(162):
        day = date(2022, 8, 1) + timedelta(days=i)
        rows.append({"data_day": day.isoformat(),
                     "reference_time_ms": int(pd.Timestamp(day+timedelta(days=1), tz="UTC").timestamp()*1000),
                     "trade_close": 100.+i, "trade_close_valid_for_history": True,
                     "partial_lifecycle_day": False, "known_lifecycle_order_block": False,
                     "scoped_execution_block": False, "known_equity_episode": False,
                     "episode_number": 1, "close_episode_number": 1, "imbalance_inputs_valid": True,
                     "base_failure_mask": 0, "trade_quote_volume_sum": 10., "taker_buy_quote_volume_sum": 6.})
    marks = [{"bar_open_ms": START+i*HOUR, "close": 100.} for i in range(24)]
    funding = [{"event_timestamp_ms": stamp, "funding_rate": .0001, "funding_interval_hours": 8}
               for stamp in range(START-7*DAY, START+2*DAY, 8*HOUR)]
    first = append_features(rows, marks, funding, "BTCUSDT")
    assert len(first) == 1 and first[0]["decision_date"] == "2023-01-02"
    assert first[0]["label"] is None
    for row in rows:
        if row["data_day"] >= "2023-01-02":
            row["trade_close"] = 999999.
            row["taker_buy_quote_volume_sum"] = 0.
    assert append_features(rows, marks, funding, "BTCUSDT") == first


def test_engine_calendar_preserves_default_and_bounds_2023():
    pytest.importorskip("nautilus_trader")
    from first_development_engine import HistoricalData

    data = HistoricalData.__new__(HistoricalData)
    data.symbols = ["BTCUSDT"]
    data.funding = {"BTCUSDT": []}
    data.mark = lambda symbol, stamp: (100., stamp)
    data.vwap = lambda symbol, stamp: 100.
    assert data.events(2021) == data.events(2021, end_year=2022)
    records = data.events(2023, end_year=2023)
    stamps = pd.to_datetime([r["stamp"] for r in records], unit="ns", utc=True)
    assert (stamps.year == 2023).all()
    assert len([r for r in records if r["kind"] == "snapshot"]) == 365
    final = [r for r in records if r["kind"] == "final"]
    assert pd.Timestamp(final[0]["stamp"], tz="UTC") == pd.Timestamp("2023-12-30 23:00", tz="UTC")


def test_training_purges_boundary_and_schedule_has_matching_universe():
    pytest.importorskip("lightgbm")
    pytest.importorskip("nautilus_trader")
    from run_validation_2023 import schedule, training_rows

    frame = pd.DataFrame({"feature_cutoff_ms": [START-DAY, START-DAY, START],
                          "label_available_ms": [START-1, START, START+DAY], "label": [1., 2., None]})
    assert list(training_rows(frame).index) == [0]
    names = [f"ASSET{i:02d}" for i in range(20)]
    sample = pd.DataFrame({"decision_date": "2023-01-02", "instrument_id": names,
                           "score": 1., "momentum60": 1.})
    portfolio = schedule(sample, "score")
    assert portfolio["2023-01-02"] == {**dict.fromkeys(names[:5], .1), **dict.fromkeys(names[-5:], -.1)}
    assert portfolio["2023-01-09"] == {}
    assert schedule(sample.iloc[:19], "score")["2023-01-02"] == {}
