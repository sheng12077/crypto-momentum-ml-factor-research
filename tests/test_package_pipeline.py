"""Synthetic cross-year accounting and reporting; no historical PnL execution."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from momentum_data.data import preflight as rules
from momentum_data.backtest import workflow as run
from momentum_data.data.benchmarks import benchmark
from momentum_data.backtest.engine import simulate


def fixture_data():
    start, stop = rules.ms("2022-12-30"), rules.ms("2023-01-08")
    change = rules.ms("2023-01-01")
    d = rules.ContinuousData.__new__(rules.ContinuousData)
    d.symbols, d.terminal_ends = ["BTCUSDT"], {}
    d.mark = lambda s, t: (100.0 if t < change else 110.0, t)
    d.vwap = lambda s, t: 100.0 if t < change else 110.0
    d.trades = {
        "BTCUSDT": {
            t: (100.0 if t < change else 110.0, 1.0, 100.0) for t in range(start, stop, rules.HOUR)
        }
    }
    d.funding = {"BTCUSDT": [(rules.ms("2022-12-31") + 8 * rules.HOUR, 0.0001), (change, 0.0001)]}
    return d, start, stop


def test_actual_quantities_funding_and_capital_survive_new_year(tmp_path):
    d, a, z = fixture_data()
    events = d.events_range(a, z - rules.DAY)
    final = (z - rules.DAY - rules.HOUR) * 1000000
    assert [e["stamp"] for e in events if e["kind"] == "final"] == [final]
    plan = {"2022-12-30": {"BTCUSDT": 1.0}}
    daily, first = simulate(d, events, plan, tmp_path / "one", bps=0)
    _, replay = simulate(d, events, plan, tmp_path / "two", bps=0)
    assert first["financial_sha256"] == replay["financial_sha256"]
    fills = pd.read_csv(tmp_path / "one/fills.csv")
    assert len(fills) == 2
    assert int(fills.timestamp_ns.iloc[-1]) == final
    assert first["ending_nav"] == pytest.approx(109874.0)
    funding = pd.read_csv(tmp_path / "one/funding.csv")
    assert funding.signed_quantity.tolist() == [1000.0, 1000.0]
    assert funding.cashflow_usdt.sum() == pytest.approx(-21.0)
    assert daily.loc[daily.timestamp == "2023-01-01T00:00:00Z", "strategy_nav"].iloc[0] != 100000
    with pytest.raises(ValueError):
        d.events_range(rules.START - rules.DAY, z - rules.DAY)


def test_plan_preflight_reports_all_gaps_and_held_terminal():
    d, a, z = fixture_data()
    d.mark = lambda s, t: None
    d.vwap = lambda s, t: None
    d.terminal_ends = {"BTCUSDT": rules.ms("2023-01-01")}
    audit = rules.audit_plan(d, {"2022-12-30": {"BTCUSDT": 1.0}}, a, z)
    assert not audit["success"]
    reasons = {x["reason"] for x in audit["problems"]}
    assert {
        "held daily mark",
        "held funding mark",
        "held terminal settlement unverified",
        "execution VWAP",
        "final liquidation VWAP",
    } <= reasons


def test_annual_schedule_keeps_frozen_phase_and_forecast_causality():
    from momentum_data.portfolio.ranking import mondays

    frame = pd.DataFrame(
        [
            {"decision_date": d, "instrument_id": f"A{i:02d}", "score": float(i)}
            for y in rules.YEARS
            for d in mondays(y)
            for i in range(20)
        ]
    )
    plan = rules.make_schedule(frame)
    assert "2022-01-03" in plan and "2022-01-10" not in plan
    assert "2023-01-02" in plan and "2023-01-09" not in plan
    assert all(len(w) == 10 and sum(w.values()) == pytest.approx(0) for w in plan.values())
    changed = frame.copy()
    changed.loc[changed.decision_date >= "2024-01-01", "score"] *= -1
    assert {d: w for d, w in rules.make_schedule(changed).items() if d < "2024-01-01"} == {
        d: w for d, w in plan.items() if d < "2024-01-01"
    }


def test_calendar_year_slices_include_january_first_bridge(monkeypatch):
    monkeypatch.setattr(run, "YEARS", (2022, 2023))
    idx = pd.date_range("2022-12-30", "2023-01-03", tz="UTC")
    daily = pd.DataFrame(
        {n: [100.0, 105.0, 126.0, 120.0, 130.0] for n in ["strategy_nav", "btc_nav", "eth_nav"]},
        index=idx,
    )
    table = run.year_slices(daily).set_index(["year", "series"])
    a = table.loc[(2022, "strategy_nav"), "total_return"]
    b = table.loc[(2023, "strategy_nav"), "total_return"]
    assert (1 + a) * (1 + b) - 1 == pytest.approx(0.3)
    assert b == pytest.approx(130 / 105 - 1)
