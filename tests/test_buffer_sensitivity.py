import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_buffer_sensitivity import choose_python, launch  # noqa: E402
from strategy_adjustment_rules import buffered_side, mondays, portfolio_schedule  # noqa: E402
from two_week_buffer_rules import RETENTION_RANKS, retain_side, schedule  # noqa: E402


def panel(day, order):
    return pd.DataFrame({"decision_date": day, "instrument_id": order, "score": range(len(order), 0, -1)})


@pytest.mark.parametrize("year", [2022, 2023])
def test_rank5_is_exact_previous_no_buffer_schedule(year):
    names = [f"A{i:02d}" for i in range(20)]
    frame = pd.concat([panel(day, names[i % 10:]+names[:i % 10]) for i, day in enumerate(mondays(year))])
    actual, audit = schedule(frame, year, 5)
    old, _ = portfolio_schedule(frame, year, weeks=2)
    assert actual == old and len(audit) == 26
    assert list(actual) == mondays(year)[::2]


def test_rank8_matches_prior_retention_primitive_and_rank_boundary():
    names = [f"A{i:02d}" for i in range(20)]
    previous = {names[0], names[5], names[7], names[8], names[10]}
    assert retain_side(names, previous, 8) == buffered_side(names, previous)
    assert names[5] in retain_side(names, previous, 6)
    assert names[7] not in retain_side(names, previous, 6)
    assert names[7] in retain_side(names, previous, 8)
    assert names[8] not in retain_side(names, previous, 8)
    assert names[8] in retain_side(names, previous, 10)
    assert names[10] not in retain_side(names, previous, 10)


def test_buffer_does_not_check_membership_on_skipped_week_and_resets_on_cash():
    names = [f"A{i:02d}" for i in range(20)]
    shifted = names[1:6]+names[:1]+names[6:]
    frame = pd.concat([panel("2023-01-02", names), panel("2023-01-09", names[:19]),
                       panel("2023-01-16", shifted), panel("2023-01-30", names[:19]),
                       panel("2023-02-13", shifted)])
    weights, _ = schedule(frame, 2023, 8)
    assert "2023-01-09" not in weights
    assert names[0] in weights["2023-01-16"]
    assert weights["2023-01-30"] == {}
    assert names[0] not in weights["2023-02-13"]
    assert set(weights["2023-02-13"]) == set(shifted[:5]+shifted[-5:])


@pytest.mark.parametrize("rank", RETENTION_RANKS)
def test_current_eligibility_ties_and_disjoint_slots(rank):
    names = [f"A{i:02d}" for i in range(21)]
    first, second = panel("2023-01-02", names), panel("2023-01-16", names[1:])
    frame = pd.concat([first, second])
    frame["score"] = 1.
    weights, _ = schedule(frame, 2023, rank)
    for day in ("2023-01-02", "2023-01-16"):
        assert len(weights[day]) == 10
        assert sum(weights[day].values()) == pytest.approx(0.)
    assert names[0] not in weights["2023-01-16"]
    with pytest.raises(ValueError, match="Duplicate"):
        schedule(pd.concat([first, first]), 2023, rank)
    with pytest.raises(ValueError, match="Unregistered"):
        schedule(first, 2023, 7)


def test_launcher_propagates_errors_and_logs_both_streams(tmp_path, monkeypatch):
    import run_buffer_sensitivity as launcher

    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "failure.py").write_text("import sys\nprint('hello stdout')\nprint('hello stderr', file=sys.stderr)\nsys.exit(7)\n")
    log = tmp_path / "test.log"
    with pytest.raises(subprocess.CalledProcessError) as error:
        launch(Path(sys.executable), "failure.py", [], log)
    assert error.value.returncode == 7
    assert "hello stdout" in log.read_text() and "hello stderr" in log.read_text()
    assert choose_python(sys.executable) == Path(sys.executable)
    with pytest.raises(FileNotFoundError):
        choose_python(tmp_path / "absent-python")


def test_summary_reports_incomplete_without_runtime_or_running(tmp_path, monkeypatch, capsys):
    import run_buffer_sensitivity as launcher

    monkeypatch.setattr(launcher, "BASE", tmp_path)
    monkeypatch.setattr(sys, "argv", ["launcher", "--stage", "summary"])
    launcher.main()
    summary = json.loads(capsys.readouterr().out)
    assert summary["success"] is False and summary["completed_cases"] == 0


def worker_module():
    pytest.importorskip("nautilus_trader")
    pytest.importorskip("lightgbm")
    import buffer_sensitivity_worker
    return buffer_sensitivity_worker


def test_checkpoint_rejects_corruption_and_contract_changes(tmp_path, monkeypatch):
    worker = worker_module()
    monkeypatch.setattr(worker, "BASE", tmp_path)
    monkeypatch.setattr(worker, "RESULTS", tmp_path / "results")
    worker.write(tmp_path / "results/run_contract.json", {"version": 1})
    worker.write(tmp_path / "preparation/2022/retain_08.json", {"weights": {}})
    folder = tmp_path / "case"
    worker.write(folder / "some_result.json", {"value": 10})
    case = {"year": 2022, "retention_rank": 8, "slippage_bps": 5, "replay": False}
    worker.checkpoint(folder, {"total_return": .1}, case)
    assert worker.read_checkpoint(folder)["case"] == case
    worker.write(folder / "some_result.json", {"value": 11})
    with pytest.raises(ValueError, match="corruption"):
        worker.read_checkpoint(folder)
    worker.write(folder / "some_result.json", {"value": 10})
    worker.write(tmp_path / "results/run_contract.json", {"version": 2})
    with pytest.raises(ValueError, match="different run contract"):
        worker.read_checkpoint(folder)


def test_comparison_requires_both_years_and_stress_outcomes():
    worker = worker_module()
    rows = []
    for year in (2022, 2023):
        for rank in RETENTION_RANKS:
            for bps in (5, 10):
                rows.append({"year": year, "retention_rank": rank, "slippage_bps": bps, "total_return": .1,
                             "Sharpe_rf0": 1. if rank == 5 else 1.2, "MDD": -.1 if rank == 5 else -.09,
                             "traded_notional": 100 if rank == 5 else 90, "other_months_compounded_return": .01})
    table = pd.DataFrame(rows)
    table.loc[(table.year == 2023) & (table.retention_rank == 8), "MDD"] = -.2
    table.loc[(table.year == 2023) & (table.retention_rank == 10) & (table.slippage_bps == 10), "total_return"] = -.1
    result = worker.comparison_table(table)
    assert result[result.retention_rank == 6][["primary_gate", "stress_positive"]].to_numpy().all()
    assert not result[result.retention_rank == 8].primary_gate.all()
    assert not result[result.retention_rank == 10].stress_positive.all()


def test_full_report_renderer_uses_synthetic_fixture_only(tmp_path, monkeypatch):
    worker_module()
    import report_buffer_sensitivity as report

    monkeypatch.setattr(report, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(report, "FIGURES", tmp_path / "figures")
    monkeypatch.setattr(report, "TABLES", tmp_path / "tables")
    called = []
    monkeypatch.setattr(report, "notebook", lambda: called.append(True))
    rows = []
    for year in (2022, 2023):
        for rank in RETENTION_RANKS:
            for bps in (5, 10):
                rows.append({"year": year, "retention_rank": rank, "slippage_bps": bps, "total_return": .1,
                             "Sharpe_rf0": 1.2 if rank == 6 else 1., "MDD": -.1,
                             "traded_notional": 100. if rank == 5 else 90., "other_months_compounded_return": .01})
            folder = tmp_path / f"results/{year}/retain_{rank:02d}/slippage_5bps"
            folder.mkdir(parents=True)
            dates = pd.date_range(f"{year}-01-01", periods=365, tz="UTC")
            pd.DataFrame({"timestamp": dates, "strategy_nav": [100000.+i for i in range(365)]}).to_csv(folder / "daily.csv", index=False)
            pd.DataFrame({"month": pd.date_range(f"{year}-01-31", periods=12, freq=pd.offsets.MonthEnd()),
                          "strategy_nav": .001}).to_csv(folder / "monthly_returns.csv", index=False)
    table = pd.DataFrame(rows)
    table.to_csv(tmp_path / "results/all_runs.csv", index=False)
    (tmp_path / "results/summary.json").write_text(json.dumps({"success": True, "completed_cases": 16,
                                                              "verified_replays": 2, "supported_retention_ranks": [6]}))
    monkeypatch.setattr(report, "verify_results", lambda: table.copy())
    report.report()
    assert called == [True]
    assert len(pd.read_csv(tmp_path / "tables/all_registered_runs.csv")) == 16
    assert (tmp_path / "figures/rank_sensitivity.png").is_file()
