"""Offline acceptance checks; never execute historical fits or simulations."""

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from crypto_factor_research.config import DAY, HOUR
from crypto_factor_research.first_window import held_intervals, ranked_schedule, training_rows
from crypto_factor_research.window_data import PublicSources, WindowData, episode_notice, ms

ROOT = Path(__file__).resolve().parents[1]


def batch():
    return runpy.run_path(str(ROOT / "scripts/run_dynamic_final_windows.py"))["run_batch"]


def test_both_preflights_precede_financial_runs(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append((command[command.index("--config") + 1], command[-1]))
        return SimpleNamespace(returncode=0)

    result = batch()(root=tmp_path, runner=runner)
    assert result["success"]
    assert [s for _, s in calls] == ["preflight", "preflight", "all", "all"]
    assert calls[0][0].endswith("2025.json") and calls[1][0].endswith("2026.json")


def test_second_preflight_failure_starts_no_financial_runs(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append(command[-1])
        return SimpleNamespace(returncode=int(len(calls) == 2))

    result = batch()(root=tmp_path, runner=runner)
    assert not result["success"] and calls == ["preflight", "preflight"]
    saved = json.loads(
        (tmp_path / "data/processed/dynamic_final_windows/batch_status.json").read_text()
    )
    assert saved["failed_step"]["config"].endswith("2026.json")


def test_summary_does_not_prepare_or_simulate(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append(command[-1])
        return SimpleNamespace(returncode=0)

    assert batch()(stage="summary", root=tmp_path, runner=runner)["success"]
    assert calls == ["summary", "summary"]


def test_partial_2026_schedule_has_no_november_decisions():
    frame = pd.DataFrame(
        {
            "instrument_id": [f"A{i}" for i in range(20)],
            "feature_cutoff_ms": ms("2026-01-05"),
            "score": range(20),
        }
    )
    schedule = ranked_schedule(frame, 2026, stop_exclusive="2026-11-01")
    assert list(schedule)[0] == "2026-01-05"
    assert list(schedule)[-1] == "2026-10-26"
    assert len(schedule) == 22
    assert all(ms(t) + 2 * HOUR < ms("2026-11-01") - DAY - HOUR for t in schedule)


@pytest.mark.parametrize("year", [2025, 2026])
def test_migration_registry_preserves_repeated_symbols_and_futures_dates(year):
    config = json.loads((ROOT / f"config/dynamic_{year}.json").read_text())
    assertions = {
        (x["symbol"], x["effective_utc"]): x["article_code"] for x in config["cessation_notices"]
    }
    expected = {
        ("BNXUSDT", "2023-02-11T04:00:00Z"): "4d23ada51a2e4fa182835c77d51ba1a9",
        ("BNXUSDT", "2025-03-17T09:00:00Z"): "2f963977c7274e0583f16f2e26987b61",
        ("LOKAUSDT", "2025-07-21T09:00:00Z"): "551eeaf9861c47b8ad3482f45abf3f38",
        ("OMNIUSDT", "2025-09-22T09:00:00Z"): "13d0a79f79ef4406963dcd7f9d1de325",
    }
    assert expected.items() <= assertions.items()


@pytest.mark.parametrize("year", [2025, 2026])
def test_configs_freeze_parameters_and_purge_future_labels(year):
    old = json.loads((ROOT / "config/dynamic_2024.json").read_text())
    config = json.loads((ROOT / f"config/dynamic_{year}.json").read_text())
    changed = {
        "spot_root",
        "output_root",
        "train_stop",
        "start",
        "stop_exclusive",
        "registration",
        "cessation_notices",
    }
    assert {k: v for k, v in old.items() if k not in changed} == {
        k: v for k, v in config.items() if k not in changed
    }
    cutoff = ms(config["start"])

    class Data:
        notices = {}

        def vwap(self, symbol, t):
            assert t < cutoff
            return 100 + t / DAY

    frame = pd.DataFrame(
        {"instrument_id": ["A", "A"], "feature_cutoff_ms": [cutoff - 10 * DAY, cutoff - DAY]}
    )
    train, _ = training_rows(frame, Data(), cutoff)
    assert len(train) == 1 and train.label_available_ms.lt(cutoff).all()
    assertions = [(x["symbol"], x["effective_utc"]) for x in config["cessation_notices"]]
    assert len(assertions) == len(set(assertions))
    assert all(int(t[:4]) <= year for _, t in assertions)


def test_two_cessations_preserve_both_holding_exit_boundaries():
    a, b = ms("2025-01-06"), ms("2025-01-20")
    first = {"symbol": "A", "effective_ms": a + 2 * DAY, "exit_ms": a + DAY, "valid_to_ms": b}
    second = {"symbol": "A", "effective_ms": b + 3 * DAY, "exit_ms": b + 2 * DAY}
    notices = {"A": first, "A@second": second}
    assert episode_notice(notices, "A", a) is first
    assert episode_notice(notices, "A", b) is second
    spans = held_intervals(
        {"2025-01-06": {"A": 0.1}, "2025-01-20": {"A": 0.1}}, notices, a, b + 10 * DAY
    )
    assert [end for _, end in spans["A"]] == [first["exit_ms"], second["exit_ms"]]


def test_relaunch_requires_correct_contract_and_advance_publication(tmp_path, monkeypatch):
    client = PublicSources(tmp_path, budget=0)
    article = {
        "success": True,
        "data": {
            "code": "launch",
            "publishDate": ms("2025-04-16") + 10 * HOUR,
            "body": json.dumps({"text": "Binance Futures AERGOUSDT Perpetual 2025-04-16 11:00"}),
        },
    }
    monkeypatch.setattr(client, "get", lambda url: (json.dumps(article).encode(), {}))
    item = {
        "symbol": "AERGOUSDT",
        "relaunch_article_code": "launch",
        "relaunch_utc": "2025-04-16T11:00:00Z",
    }
    assert client.relaunch(item)[0] == ms("2025-04-16") + 11 * HOUR
    article["data"]["publishDate"] += HOUR
    with pytest.raises(ValueError, match="before reopening"):
        client.relaunch(item)


def test_dual_candidate_report_outputs_with_tiny_saved_ledgers(tmp_path, monkeypatch):
    from crypto_factor_research import window_audit, window_report

    path = tmp_path / "run"
    path.mkdir()
    cases = ["lightgbm", "equal_groups", "momentum60", "random_1000"]
    (path / "simulation_summary.json").write_text(
        json.dumps(
            {
                "success": True,
                "completed_cases": 4,
                "primary_replay_identical": True,
                "cases": [{"case": name, "bps": 5} for name in cases],
            }
        )
    )
    times = [f"2025-01-{d:02}T00:00:00Z" for d in [1, 2, 3]]
    benchmark = pd.DataFrame({"timestamp": times, "nav": [100000.0, 101000.0, 100500.0]})
    monkeypatch.setattr(window_report, "spot_benchmark", lambda *args: (benchmark.copy(), {}))
    monkeypatch.setattr(window_audit, "audit_all", lambda *args: {"success": True})
    asset = pd.DataFrame({"net_pnl_usdt": [1.0]}, index=pd.Index(["A"], name="instrument_id"))
    side = pd.DataFrame({"net_pnl_usdt": [1.0, 0.0]}, index=["long", "short"])
    monkeypatch.setattr(window_audit, "attribution", lambda *args: (asset, side))
    for i, name in enumerate(cases):
        folder = path / "results" / f"{name}_5bps"
        folder.mkdir(parents=True)
        (folder / "case_manifest.json").write_text("{}")
        pd.DataFrame(
            {
                "timestamp": times,
                "strategy_nav": [100000.0, 100500.0 + i * 100, 101000.0 + i * 300],
                "commissions_usdt": [0.0, 1.0, 1.0],
                "funding_cashflow_usdt": [0.0, 2.0, -1.0],
                "traded_notional_usdt": [0.0, 2000.0, 2000.0],
            }
        ).to_csv(folder / "engine_daily.csv", index=False)
    config = {
        "start": "2025-01-01",
        "stop_exclusive": "2025-01-04",
        "train_start": "2021-01-01",
        "train_stop": "2025-01-01",
    }
    result = window_report.report(tmp_path, config, path)
    assert {x["case"] for x in result["candidate_comparison"]} == {
        "lightgbm_5bps",
        "equal_groups_5bps",
        "momentum60_5bps",
    }
    monthly = pd.read_csv(path / "report/candidate_monthly_returns.csv")
    assert "equal_groups_5bps" in monthly and "lightgbm_5bps" in monthly
    assert (path / "report/equity.png").is_file()
    assert (path / "report/monthly_returns.png").is_file()


def test_repeated_contract_exits_reach_events_and_independent_price_oracle():
    from crypto_factor_research.window_audit import Oracle

    start, last = ms("2025-01-01"), ms("2025-01-05")
    stamps = list(range(start - HOUR, last + HOUR, HOUR))
    bars = pd.DataFrame(
        [
            {
                "instrument_id": s,
                "bar_open_ms": t,
                "close": 100.0,
                "volume": 1.0,
                "quote_volume": 100.0,
            }
            for s in ["BTCUSDT", "A"]
            for t in stamps
        ]
    )
    first = {
        "symbol": "A",
        "effective_ms": start + DAY,
        "exit_ms": start + 60000,
        "valid_to_ms": start + 2 * DAY,
        "exit_vwap": 90.0,
    }
    second = {
        "symbol": "A",
        "effective_ms": start + 4 * DAY,
        "exit_ms": start + 3 * DAY + 60000,
        "exit_vwap": 110.0,
    }
    notices = {"A": first, "A@second": second}
    data = WindowData(
        {"trade": bars, "mark": bars, "funding": pd.DataFrame(columns=["instrument_id"])}, notices
    )
    data.exit_prices = {key: n["exit_vwap"] for key, n in notices.items()}
    events = data.events(start, last, set())
    oracle = Oracle.__new__(Oracle)
    oracle.notices = notices
    for n in notices.values():
        match = [
            e
            for e in events
            if e["symbol"] == "A" and e["kind"] == "final" and e["stamp"] == n["exit_ms"] * 1000000
        ]
        assert len(match) == 1 and match[0]["price"] == n["exit_vwap"]
        assert oracle.fill_price("A", n["exit_ms"], last) == n["exit_vwap"]
