import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from strategy_adjustment_rules import (  # noqa: E402
    CONFIGS,
    buffered_side,
    mondays,
    portfolio_schedule,
    training_rows,
)


def panel(day, order):
    return pd.DataFrame({"decision_date": day, "instrument_id": order,
                         "score": list(range(len(order), 0, -1))})


def test_buffer_retains_rank6_then_exits_rank9_and_replaces_from_top5():
    names = [f"A{i:02d}" for i in range(1, 21)]
    second = names[1:6]+names[:1]+names[6:]
    third = names[1:9]+names[:1]+names[9:]
    frame = pd.concat([panel("2023-01-02", names), panel("2023-01-09", second),
                       panel("2023-01-16", third)])
    schedule, _ = portfolio_schedule(frame, 2023, buffer=True)
    def longs(day):
        return {name for name, weight in schedule[day].items() if weight > 0}
    assert longs("2023-01-02") == set(names[:5])
    assert longs("2023-01-09") == set(names[:5])
    assert longs("2023-01-16") == set(names[1:6])
    assert all(len(weights) in (0, 10) and sum(weights.values()) == pytest.approx(0) for weights in schedule.values())


def test_buffer_resets_on_cash_and_reenters_without_old_membership():
    names = [f"A{i:02d}" for i in range(20)]
    shifted = names[1:6]+names[:1]+names[6:]
    frame = pd.concat([panel("2023-01-02", names), panel("2023-01-09", names[:19]),
                       panel("2023-01-16", shifted)])
    schedule, _ = portfolio_schedule(frame, 2023, buffer=True)
    assert schedule["2023-01-09"] == {}
    assert {k for k, v in schedule["2023-01-16"].items() if v > 0} == set(shifted[:5])
    assert buffered_side(names, {"not-eligible"}) == names[:5]
    assert buffered_side(list(reversed(names)), set(names[-5:])) == list(reversed(names))[:5]


@pytest.mark.parametrize("year,first", [(2022, "2022-01-03"), (2023, "2023-01-02")])
def test_fixed_cadence_phase_and_ties(year, first):
    names = [f"A{i:02d}" for i in range(20)]
    frame = pd.concat([panel(day, names) for day in mondays(year)])
    frame["score"] = 1.
    two, _ = portfolio_schedule(frame, year, weeks=2)
    four, _ = portfolio_schedule(frame, year, weeks=4)
    assert list(two) == mondays(year)[::2] and len(two) == 26
    assert list(four) == mondays(year)[::4] and len(four) == 13
    assert next(iter(two)) == first
    assert set(two[first]) == set(names[:5]+names[-5:])
    with pytest.raises(ValueError, match="Unregistered"):
        portfolio_schedule(frame, year, weeks=2, buffer=True)


def test_training_purge_and_fixed_ablation_groups():
    frame = pd.DataFrame({"feature_cutoff_ms": [9, 9, 10], "label_available_ms": [9, 10, 11],
                          "label": [1., 2., None]})
    assert training_rows(frame, 10).label.tolist() == [1.]
    assert CONFIGS["F_no_momentum"]["drop"] == ["momentum20", "momentum60", "momentum120"]
    assert CONFIGS["G_no_funding"]["drop"] == ["funding7"]


def test_nautilus_skips_unscheduled_week_and_keeps_quantity(tmp_path):
    pytest.importorskip("nautilus_trader")
    from first_development_engine import HistoricalData, simulate

    data = HistoricalData.__new__(HistoricalData)
    data.symbols, data.funding = ["BTCUSDT"], {"BTCUSDT": []}
    data.mark = lambda symbol, stamp: (10000., stamp)
    data.vwap = lambda symbol, stamp: 10000.
    data.trades = {"BTCUSDT": {int(pd.Timestamp(day, tz="UTC").timestamp()*1000): (10000., 10., 100000.)
                                for day in mondays(2022)}}
    schedule = {"2022-01-03": {"BTCUSDT": .1}, "2022-01-17": {"BTCUSDT": .1}}
    _, result = simulate(data, data.events(2022), schedule, tmp_path, bps=0)
    assert result["success"]
    targets = pd.read_csv(tmp_path / "targets.csv")
    assert targets.decision_date.tolist() == ["2022-01-03", "2022-01-17"]
    fills = pd.read_csv(tmp_path / "fills.csv")
    days = pd.to_datetime(fills.timestamp_ns, unit="ns", utc=True).dt.strftime("%Y-%m-%d")
    assert "2022-01-10" not in set(days)
    assert fills.quantity.iloc[0] == 1.
