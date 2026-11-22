"""Synthetic cross-year accounting and reporting; no historical PnL execution."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import continuous_reconstruction as rules
import run_continuous_reconstruction as run
from build_final_holdout_spot import benchmark
from final_holdout_engine import simulate


def fixture_data():
    start, stop = rules.ms("2022-12-30"), rules.ms("2023-01-08")
    change = rules.ms("2023-01-01")
    d = rules.ContinuousData.__new__(rules.ContinuousData)
    d.symbols, d.terminal_ends = ["BTCUSDT"], {}
    d.mark = lambda s,t: (100. if t < change else 110., t)
    d.vwap = lambda s,t: 100. if t < change else 110.
    d.trades = {"BTCUSDT": {t: (100. if t < change else 110., 1., 100.) for t in range(start, stop, rules.HOUR)}}
    d.funding = {"BTCUSDT": [(rules.ms("2022-12-31")+8*rules.HOUR,.0001), (change,.0001)]}
    return d, start, stop


def test_actual_quantities_funding_and_capital_survive_new_year(tmp_path):
    d,a,z = fixture_data()
    events = d.events_range(a,z-rules.DAY)
    final = (z-rules.DAY-rules.HOUR)*1000000
    assert [e["stamp"] for e in events if e["kind"] == "final"] == [final]
    plan = {"2022-12-30": {"BTCUSDT":1.}}
    daily, first = simulate(d, events, plan, tmp_path/"one", bps=0)
    _, replay = simulate(d, events, plan, tmp_path/"two", bps=0)
    assert first["financial_sha256"] == replay["financial_sha256"]
    fills = pd.read_csv(tmp_path/"one/fills.csv")
    assert len(fills) == 2
    assert int(fills.timestamp_ns.iloc[-1]) == final
    assert first["ending_nav"] == pytest.approx(109874.)
    funding = pd.read_csv(tmp_path/"one/funding.csv")
    assert funding.signed_quantity.tolist() == [1000.,1000.]
    assert funding.cashflow_usdt.sum() == pytest.approx(-21.)
    assert daily.loc[daily.timestamp == "2023-01-01T00:00:00Z","strategy_nav"].iloc[0] != 100000
    with pytest.raises(ValueError):
        d.events_range(rules.START-rules.DAY,z-rules.DAY)


def test_plan_preflight_reports_all_gaps_and_held_terminal():
    d,a,z = fixture_data()
    d.mark = lambda s,t: None
    d.vwap = lambda s,t: None
    d.terminal_ends = {"BTCUSDT":rules.ms("2023-01-01")}
    audit = rules.audit_plan(d,{"2022-12-30":{"BTCUSDT":1.}},a,z)
    assert not audit["success"]
    reasons = {x["reason"] for x in audit["problems"]}
    assert {"held daily mark","held funding mark","held terminal settlement unverified","execution VWAP","final liquidation VWAP"} <= reasons


def test_annual_schedule_keeps_frozen_phase_and_forecast_causality():
    from strategy_adjustment_rules import mondays
    frame = pd.DataFrame([{"decision_date":d,"instrument_id":f"A{i:02d}","score":float(i)}
                          for y in rules.YEARS for d in mondays(y) for i in range(20)])
    plan = rules.make_schedule(frame)
    assert "2022-01-03" in plan and "2022-01-10" not in plan
    assert "2023-01-02" in plan and "2023-01-09" not in plan
    assert all(len(w)==10 and sum(w.values())==pytest.approx(0) for w in plan.values())
    changed = frame.copy()
    changed.loc[changed.decision_date >= "2024-01-01","score"] *= -1
    assert {d:w for d,w in rules.make_schedule(changed).items() if d < "2024-01-01"} == {d:w for d,w in plan.items() if d < "2024-01-01"}


def test_calendar_year_slices_include_january_first_bridge(monkeypatch):
    monkeypatch.setattr(run,"YEARS",(2022,2023))
    idx = pd.date_range("2022-12-30","2023-01-03",tz="UTC")
    daily = pd.DataFrame({n:[100.,105.,126.,120.,130.] for n in ["strategy_nav","btc_nav","eth_nav"]},index=idx)
    table = run.year_slices(daily).set_index(["year","series"])
    a=table.loc[(2022,"strategy_nav"),"total_return"]
    b=table.loc[(2023,"strategy_nav"),"total_return"]
    assert (1+a)*(1+b)-1 == pytest.approx(.3)
    assert b == pytest.approx(130/105-1)


def test_complete_pipeline_audits_collision_renders_and_rejects_corruption(tmp_path,monkeypatch):
    d,a,z = fixture_data()
    # Closing trade collides with funding: charge the old quantity before executing exit.
    collision = rules.ms("2023-01-02")+2*rules.HOUR
    d.funding["BTCUSDT"].append((collision,.0002))
    events = d.events_range(a,z-rules.DAY)
    plan={"2022-12-30":{"BTCUSDT":1.},"2023-01-02":{}}
    base=tmp_path/"data";base.mkdir()
    (base/"contract.json").write_text("{}")
    monkeypatch.setattr(run,"BASE",base)
    monkeypatch.setattr(run,"ROOT",tmp_path)
    monkeypatch.setattr(run,"START",a);monkeypatch.setattr(run,"STOP",z)
    monkeypatch.setattr(run,"YEARS",(2022,2023))
    monkeypatch.setattr(run,"TABLES",tmp_path/"tables")
    monkeypatch.setattr(run,"FIGURES",tmp_path/"figures")
    monkeypatch.setattr(run,"ContinuousData",lambda _:d)
    monkeypatch.setattr(run,"require_preflight",lambda:None)
    original_audit=run.audit_case
    monkeypatch.setattr(run,"audit_case",lambda data,folder,bps:original_audit(data,folder,bps,start=a,stop=z))
    observed={t:{"close":100. if t < rules.ms("2023-01-01") else 110.,"volume":1.,"quote":100.} for t in range(a,z,rules.HOUR)}
    nav,_=benchmark(observed,a,z)
    for symbol in ("BTCUSDT","ETHUSDT"):
        nav.to_csv(base/f"{symbol}_spot.csv",index=False)
    cached={}
    for y in (2022,2023):
        f=tmp_path/str(y);f.mkdir()
        pd.DataFrame({"shap_"+n:[.01,.02] for n in rules.FEATURES}).to_csv(f/"shap_values.csv",index=False)
        cached[y]=f
    monkeypatch.setattr(run,"MODEL_ROOTS",cached)
    # Fixed five-panel plotting supports annual subsets in fixtures.
    for name,bps in (("slippage_5bps",5),("slippage_10bps",10),("primary_replay",5)):
        run.case(d,events,plan,name,bps)
    fund=pd.read_csv(base/"results/slippage_5bps/funding.csv")
    assert fund.loc[fund.timestamp_ns == collision*1000000,"signed_quantity"].iloc[0] == 1000
    run.write(base/"simulation_complete.json",{"success":True,"output_hashes":{}})
    run.report()
    summary=json.loads((base/"summary.json").read_text())
    assert summary["report_verified"] and not summary["fresh_OOS"]
    assert (run.FIGURES/"dashboard_5bps.png").exists()
    assert (run.TABLES/"year_boundaries.csv").exists()
    run.print_summary()
    import nbformat
    notebook = nbformat.read(Path(__file__).resolve().parents[1] / "notebooks/continuous_reconstruction_results.ipynb", as_version=4)
    nbformat.validate(notebook)
    namespace = {}
    for cell in notebook.cells:
        if cell.cell_type == "code":
            exec(compile(cell.source, "continuous_results_notebook", "exec"), namespace)
    (run.TABLES/"metrics_5bps.csv").write_text("corrupted")
    with pytest.raises(ValueError,match="Report artifacts changed"):
        run.print_summary()
    fills=base/"results/slippage_5bps/fills.csv"
    bad=pd.read_csv(fills);bad.loc[0,"commission_usdt"]+=1;bad.to_csv(fills,index=False)
    with pytest.raises(ValueError,match="fee mismatch"):
        run.audit_case(d,base/"results/slippage_5bps",5)
