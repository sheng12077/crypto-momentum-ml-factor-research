import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from portfolio_weighting_rules import (  # noqa: E402
    DAY,
    HOUR,
    SCHEMES,
    DailyRisk,
    build_schedule,
    capped_weights,
)


def test_capped_weights_redistribute_budget_without_leverage():
    assert capped_weights([100, 1, 1, 1, 1]) == pytest.approx([.15, .0875, .0875, .0875, .0875])
    assert capped_weights([100, 100, 1, 1, 1]) == pytest.approx([.15, .15, .2/3, .2/3, .2/3])
    assert capped_weights([1]*5) == pytest.approx([.1]*5)
    for invalid in ([], [0]*5, [1, -1, 1, 1, 1], [float("nan")]*5):
        with pytest.raises(ValueError):
            capped_weights(invalid)


def risk_prices():
    cutoff = int(pd.Timestamp("2022-01-03", tz="UTC").timestamp()*1000)
    returns = np.tile([.01, -.01], 30)
    prices = np.r_[100., 100.*np.cumprod(1+returns)]
    return cutoff, pd.DataFrame({"instrument_id": "BTCUSDT", "bar_open_ms": cutoff-60*DAY+np.arange(61, dtype=np.int64)*DAY-HOUR,
                                  "close": prices})


def test_risk_uses_60_returns_known_at_cutoff_not_future_values():
    cutoff, frame = risk_prices()
    expected = DailyRisk(frame).estimate("BTCUSDT", cutoff)
    assert expected["sigma_daily_raw"] == pytest.approx(np.tile([.01, -.01], 30).std(ddof=1))
    future = frame.iloc[[-1]].copy()
    future["bar_open_ms"] += 20*DAY
    future["close"] = 1e12
    assert DailyRisk(pd.concat([frame, future])).estimate("BTCUSDT", cutoff) == expected
    assert expected["risk_first_available_ms"] == cutoff-60*DAY
    assert expected["risk_last_available_ms"] == cutoff
    with pytest.raises(ValueError, match="61consecutive"):
        DailyRisk(frame.drop(index=20)).estimate("BTCUSDT", cutoff)
    with pytest.raises(ValueError, match="61consecutive"):
        DailyRisk(frame.iloc[:-1]).estimate("BTCUSDT", cutoff)


def test_risk_floor_invalid_price_and_unopened_scope():
    cutoff, frame = risk_prices()
    frame["close"] = 100.
    assert DailyRisk(frame).estimate("BTCUSDT", cutoff)["sigma_daily_used"] == .005
    frame.loc[10, "close"] = 0.
    with pytest.raises(ValueError, match="Invalid risk prices"):
        DailyRisk(frame).estimate("BTCUSDT", cutoff)
    frame.loc[10, "bar_open_ms"] = 1704067200000
    with pytest.raises(ValueError, match="scope"):
        DailyRisk(frame)


def test_all_schemes_preserve_names_dates_budgets_and_short_order():
    names = [f"ASSET{i:02d}" for i in range(20)]
    sample = pd.DataFrame({"decision_date": "2022-01-03", "instrument_id": names, "score": range(20, 0, -1)})
    risk = SimpleNamespace(estimate=lambda symbol, cutoff: {"sigma_daily_used": .005+.001*names.index(symbol)})
    plans = {scheme: build_schedule(sample, 2022, scheme, risk)[0] for scheme in SCHEMES}
    for plan in plans.values():
        assert len(plan) == 26 and "2022-01-10" not in plan
        assert set(plan["2022-01-03"]) == set(names[:5]+names[-5:])
        values = np.array(list(plan["2022-01-03"].values()))
        assert values[values > 0].sum() == pytest.approx(.5)
        assert values[values < 0].sum() == pytest.approx(-.5)
        assert np.abs(values).max() <= .15
    assert plans["EQ"]["2022-01-03"][names[0]] == .1
    assert plans["RANK"]["2022-01-03"][names[0]] == .125
    assert plans["RANK"]["2022-01-03"][names[-1]] == -.125
    assert plans["RANK"]["2022-01-03"][names[-5]] == -.075


def test_synthetic_nautilus_unequal_weights_quantity_funding_and_cash(tmp_path):
    pytest.importorskip("nautilus_trader")
    from first_development_engine import simulate

    start = 1641168000000
    prices = {"BTCUSDT": 100., "ETHUSDT": 200.}
    data = SimpleNamespace(symbols=list(prices), trades={s: {start: (p, 10., p*10)} for s, p in prices.items()})
    events = []

    def add(symbol, stamp, kind, mark=False, offset=0, rate=None):
        events.append({"symbol": symbol, "stamp": stamp*1_000_000+offset, "kind": kind,
                       "price": prices[symbol], "mark_at": stamp if mark else None, "rate": rate})

    for symbol in prices:
        add(symbol, start, "mark", True)
        add(symbol, start+HOUR, "reference", True)
        add(symbol, start+2*HOUR, "execution")
        add(symbol, start+DAY, "mark", True)
        add(symbol, start+DAY, "final", offset=1)
    add("BTCUSDT", start, "snapshot", offset=100)
    add("BTCUSDT", start+HOUR, "decision", offset=100)
    add("BTCUSDT", start+2*HOUR, "check", offset=100)
    add("BTCUSDT", start+8*HOUR, "funding", True, rate=.001)
    add("ETHUSDT", start+8*HOUR, "funding", True, rate=.002)
    add("BTCUSDT", start+DAY, "final_check", offset=2)
    add("BTCUSDT", start+DAY, "snapshot", offset=100)
    _, result = simulate(data, sorted(events, key=lambda r: (r["stamp"], r["symbol"])),
                         {"2022-01-03": {"BTCUSDT": .125, "ETHUSDT": -.125}}, tmp_path, bps=0)
    assert result["ending_nav"] == pytest.approx(99987.5, abs=.01)
    fills = pd.read_csv(tmp_path / "fills.csv")
    assert fills.quantity.iloc[:2].tolist() == [125., 62.5]
    assert pd.read_csv(tmp_path / "funding.csv").cashflow_usdt.sum() == pytest.approx(12.5)
