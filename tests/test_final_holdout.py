"""Final-window safety tests: synthetic data only, no canonical/holdout reads."""
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_final_holdout_spot import benchmark, normalize_row
from final_holdout_common import (
    CODE, DAY, FEATURES, HOUR, ROOT, START, STOP, WINDOWS, bind,
    features_for_dates, matured_training, mondays, ms, schedules, window_schedule, write,
)
from final_holdout_engine import FinalHistoricalData
from first_development_engine import simulate


def test_fold_calendars_and_stable_two_week_membership():
    assert [len(mondays(y)) for y in (2025, 2026)] == [52, 43]
    assert mondays(2025)[0] == date(2025, 1, 6)
    assert mondays(2026)[0] == date(2026, 1, 5)
    assert mondays(2026)[-1] == date(2026, 10, 26)
    assert [(b-a)//DAY for a, b in WINDOWS.values()] == [365, 304, 669]
    names = [f"A{i:02d}" for i in range(20)]
    frame = pd.DataFrame([{"decision_date": d.isoformat(), "feature_cutoff_ms": ms(d.isoformat()),
        "instrument_id": n, "score": 1., "momentum60": 1.}
        for y in (2025, 2026) for d in mondays(y) for n in names])
    plan = schedules(frame)
    assert len(window_schedule(plan, "2025")) == 26
    assert len(window_schedule(plan, "2026_partial")) == 22
    assert plan["2025-01-06"] == {**dict.fromkeys(names[:5], .1), **dict.fromkeys(names[-5:], -.1)}
    assert "2025-01-13" not in plan
    assert "2026-11-02" not in plan
    assert schedules(frame, "momentum60") == plan
    assert all(len(v) == 10 and sum(v.values()) == pytest.approx(0) for v in plan.values())


@pytest.mark.parametrize("cutoff", [ms("2025-01-01"), ms("2026-01-01")])
def test_purge_maturity_preserves_known_labels_and_never_reads_future(cutoff):
    cuts = [cutoff-20*DAY, cutoff-14*DAY, cutoff-7*DAY, cutoff]
    frame = pd.DataFrame([{**dict.fromkeys(FEATURES, .01), "decision_date": str(i),
        "instrument_id": "BTCUSDT", "feature_cutoff_ms": t,
        "label_available_ms": t+7*DAY+3*HOUR, "label": .7 if i == 0 else None}
        for i, t in enumerate(cuts)])
    trades = pd.DataFrame({"instrument_id": "BTCUSDT",
        "bar_open_ms": [cuts[1]+HOUR, cuts[1]+7*DAY+HOUR, cutoff+HOUR],
        "volume": [1., 1., 1.], "quote_volume": [100., 110., 999999.]})
    before = frame.copy(deep=True)
    train = matured_training(frame, trades, cutoff)
    assert list(train.label) == pytest.approx([.7, .1])
    assert (train.label_available_ms < cutoff).all()
    trades.loc[trades.bar_open_ms >= cutoff, "quote_volume"] = .00001
    pd.testing.assert_frame_equal(train, matured_training(frame, trades, cutoff), check_exact=True)
    pd.testing.assert_frame_equal(frame, before, check_exact=True)


def test_features_match_frozen_definition_and_ignore_future():
    from prepare_validation_2024 import append_features
    rows = []
    for i in range(162):
        day = date(2023, 8, 1)+timedelta(days=i)
        rows.append({"data_day": day.isoformat(), "reference_time_ms": ms((day+timedelta(days=1)).isoformat()),
            "trade_close": 100.+i, "trade_close_valid_for_history": True,
            "partial_lifecycle_day": False, "known_lifecycle_order_block": False,
            "scoped_execution_block": False, "known_equity_episode": False,
            "episode_number": 1, "close_episode_number": 1, "imbalance_inputs_valid": True,
            "base_failure_mask": 0, "trade_quote_volume_sum": .11,
            "taker_buy_quote_volume_sum": .07})
    cutoff = ms("2024-01-01")
    marks = [{"bar_open_ms": cutoff-DAY+i*HOUR} for i in range(24)]
    funding = [{"event_timestamp_ms": t, "funding_rate": .0001, "funding_interval_hours": 8}
               for t in range(cutoff-7*DAY, cutoff, 8*HOUR)]
    actual = features_for_dates(rows, marks, funding, "BTCUSDT", [date(2024, 1, 1)])
    assert actual == append_features(rows, marks, funding, "BTCUSDT")
    for row in rows:
        if row["data_day"] >= "2024-01-01":
            row["trade_close"] = 999999.
    assert actual == features_for_dates(rows, marks, funding, "BTCUSDT", [date(2024, 1, 1)])


def test_spot_microsecond_normalization_and_partial_cash_budget():
    start = ms("2025-01-01")
    raw_ms = [str(start), "100", "100", "100", "100", "1", str(start+HOUR-1), "100", "1", "1", "50", "0"]
    raw_us = raw_ms.copy()
    raw_us[0], raw_us[6] = str(start*1000), str((start+HOUR)*1000-1)
    assert normalize_row(raw_ms) == (raw_ms, "ms")
    assert normalize_row(raw_us) == (raw_ms, "us")
    raw_us[0] = str(start*1000+1)
    with pytest.raises(ValueError, match="aligned"):
        normalize_row(raw_us)
    observed = {t: {"close": 100., "volume": 1., "quote": 100.}
                for t in range(start, start+3*DAY, HOUR)}
    daily, ledger = benchmark(observed, start, start+3*DAY)
    assert len(daily) == 3 and daily.strategy_nav.iloc[0] == 100000.
    expected = 100000/(100*1.0005*1.001)*(100*.9995)*.999
    assert ledger["final_nav"] == pytest.approx(expected)
    assert daily.strategy_nav.iloc[-1] == pytest.approx(expected)


def synthetic_data():
    data = FinalHistoricalData.__new__(FinalHistoricalData)
    start, last = ms("2025-12-30"), ms("2026-01-07")
    change = ms("2026-01-01")
    data.symbols = ["BTCUSDT"]
    data.funding = {"BTCUSDT": [(ms("2025-12-31")+8*HOUR, .0001), (change, .0001)]}
    data.mark = lambda symbol, t: (100. if t < change else 110., t)
    data.vwap = lambda symbol, t: 100. if t < change else 110.
    data.trades = {"BTCUSDT": {t: (100. if t < change else 110., 1., 100.)
                              for t in range(start, last+1, DAY)}}
    return data, start, last


def test_partial_end_and_cross_year_holdings_funding_and_replay(tmp_path):
    data, start, last = synthetic_data()
    events = data.events_range(start, last)
    finals = [e for e in events if e["kind"] == "final"]
    assert len(finals) == 1 and finals[0]["stamp"] == (last-HOUR)*1000000
    assert not any(e["kind"] == "final" and e["stamp"] < ms("2026-01-01")*1000000 for e in events)
    plan = {"2025-12-30": {"BTCUSDT": 1.}}
    daily, result = simulate(data, events, plan, tmp_path / "primary", bps=0)
    _, replay = simulate(data, events, plan, tmp_path / "replay", bps=0)
    assert result["financial_sha256"] == replay["financial_sha256"]
    assert result["ending_nav"] == pytest.approx(109874.)
    fund = pd.read_csv(tmp_path / "primary/funding.csv")
    assert fund.signed_quantity.tolist() == [1000., 1000.]
    assert fund.cashflow_usdt.sum() == pytest.approx(-21.)
    assert daily.loc[daily.timestamp == "2026-01-01T00:00:00Z", "strategy_nav"].iloc[0] != 100000.
    with pytest.raises(ValueError):
        data.events_range(START-DAY, last)
    with pytest.raises(ValueError):
        data.events_range(start, STOP)


def test_complete_marker_rejects_corruption_and_contract_change(tmp_path):
    from run_final_holdout_cases import verify_case
    path = tmp_path / "ledger.csv"
    path.write_text("cash\n100000\n")
    key = ["continuous", "lightgbm", 5, False]
    write(tmp_path / "_complete.json", {"key": key, "run_contract_sha256": "abc", "result": {},
        "output_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}})
    assert verify_case(tmp_path, key, "abc") == {}
    with pytest.raises(ValueError):
        verify_case(tmp_path, key, "changed")
    path.write_text("cash\n99999\n")
    with pytest.raises(ValueError, match="Changed"):
        verify_case(tmp_path, key, "abc")
    bind(tmp_path / "contract.json", {"x": 1})
    with pytest.raises(ValueError, match="contract"):
        bind(tmp_path / "contract.json", {"x": 2})


def test_runner_lock_uses_a_file_inside_output_directory(tmp_path, monkeypatch):
    import run_final_holdout as runner
    class FakeProcess:
        stdout = []
        def __init__(self, *args, **kwargs):
            pass
        def wait(self):
            return 0
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BASE", tmp_path / "output")
    monkeypatch.setattr(runner.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(sys, "argv", ["run_final_holdout.py", "--stage", "prepare"])
    runner.main()
    assert (tmp_path / "output").is_dir()
    assert (tmp_path / "output/.run.lock").is_file()


def test_contract_inventory_and_safe_notebook():
    assert all((ROOT / "scripts" / n).exists() for n in CODE)
    book = nbformat.read(ROOT / "notebooks/final_holdout_results.ipynb", as_version=4)
    nbformat.validate(book)
    cells = [c for c in book.cells if c.cell_type == "code"]
    assert len(cells) == 4
    assert all(c.execution_count is None and not c.outputs for c in cells)


def test_model_cache_roundtrip_with_filtered_training_indices(tmp_path, monkeypatch):
    import run_final_holdout_cases as runner
    rng = np.random.default_rng(42)
    train = pd.DataFrame(rng.normal(size=(600, 5)), columns=FEATURES)
    train["label"] = .01*train.momentum20+.005*train.funding7
    train["label_available_ms"] = ms("2024-12-01")
    train.index = np.arange(len(train))*2
    val = pd.DataFrame(rng.normal(size=(20, 5)), columns=FEATURES)
    val["decision_date"], val["instrument_id"] = "2025-01-06", [f"A{i}" for i in range(20)]
    val["feature_cutoff_ms"], val["label"] = ms("2025-01-06"), np.nan
    monkeypatch.setattr(runner, "RESULTS", tmp_path)
    monkeypatch.setattr(runner, "samples", lambda y: (train.copy(), val.copy()))
    first = runner.model_scores(2025)
    def no_second_fit(**kwargs):
        raise AssertionError("Cache reload must not fit again")
    monkeypatch.setattr(runner.lgb, "LGBMRegressor", no_second_fit)
    second = runner.model_scores(2025)
    pd.testing.assert_frame_equal(first.reset_index(drop=True), second.reset_index(drop=True), check_exact=True)


def test_failed_http_consumes_persistent_budget_without_retry(tmp_path, monkeypatch):
    import urllib.error
    import final_holdout_acquisition as acquisition
    calls = []
    def fail(self, label, url, limit):
        calls.append(label)
        raise urllib.error.HTTPError(url, 429, "rate limited", {}, None)
    monkeypatch.setattr(acquisition.ProbeClient, "get", fail)
    client = acquisition.Archives(tmp_path, 1, 1024, 1)
    monkeypatch.setattr(client.pace, "wait", lambda: None)
    with pytest.raises(urllib.error.HTTPError):
        client.fetch("one", "https://data.binance.vision/example.zip")
    assert calls == ["checksum"]
    assert json.loads((tmp_path / "budget.json").read_text())["requests"] == 1
    other = acquisition.Archives(tmp_path, 1, 1024, 1)
    monkeypatch.setattr(other.pace, "wait", lambda: None)
    with pytest.raises(ValueError, match="budget"):
        other.fetch("one", "https://data.binance.vision/example.zip")
    assert calls == ["checksum"]


def test_synthetic_report_renders_all_windows_and_shared_year_anchor(tmp_path, monkeypatch):
    import report_final_holdout as report
    from momentum_data.backtest_analysis import performance_tables, validate_daily
    results, figures, tables = [tmp_path / n for n in ("results", "figures", "tables")]
    monkeypatch.setattr(report, "RESULTS", results)
    monkeypatch.setattr(report, "FIGURES", figures)
    monkeypatch.setattr(report, "TABLES", tables)
    rows = []
    for name, (a, z) in WINDOWS.items():
        dates = pd.date_range(pd.Timestamp(a, unit="ms", tz="UTC"), pd.Timestamp(z-DAY, unit="ms", tz="UTC"))
        nav = 100000+np.arange(len(dates))*10.
        daily = pd.DataFrame({"timestamp": dates, "strategy_nav": nav, "btc_nav": nav,
            "eth_nav": nav, "commissions_usdt": 0., "funding_cashflow_usdt": 0.,
            "traded_notional_usdt": 0., "gross_exposure": .1, "net_exposure": 0.})
        metrics, monthly = performance_tables(validate_daily(daily))
        for model in ("lightgbm", "momentum60"):
            folder = results / f"{name}/{model}/slippage_5bps"
            folder.mkdir(parents=True)
            daily.to_csv(folder / "daily.csv", index=False)
            metrics.to_csv(folder / "metrics.csv")
            monthly.to_csv(folder / "monthly_returns.csv")
            for bps in (5, 10):
                rows.append({"window": name, "model": model, "slippage_bps": bps, "total_return": .01})
    for year in (2025, 2026):
        folder = results / f"models/{year}"
        folder.mkdir(parents=True)
        pd.Series(np.arange(5)/100, index=FEATURES, name="mean_absolute_SHAP").to_csv(folder / "shap_importance.csv")
    report.render(pd.DataFrame(rows))
    assert len(pd.read_csv(tables / "primary_metrics.csv")) == 12
    slices = pd.read_csv(tables / "continuous_year_slices.csv")
    assert set(slices[slices.continuous_year_slice == 2025].daily_observations) == {365}
    assert set(slices[slices.continuous_year_slice == 2026].daily_observations) == {303}
    assert (figures / "continuous_dashboard.png").exists()
    assert (figures / "shap.png").exists()


def test_last_snapshot_monday_has_no_post_endpoint_decisions():
    data, start, _ = synthetic_data()
    last = ms("2026-01-05")
    events = data.events_range(start, last)
    assert max(e["stamp"] for e in events) <= last*1000000+100


@pytest.mark.parametrize("all_cash", [False, True])
def test_actual_synthetic_case_export_and_verified_resume(tmp_path, monkeypatch, all_cash):
    import run_final_holdout_cases as runner
    data, start, last = synthetic_data()
    results, spot = tmp_path / "results", tmp_path / "spot"
    spot.mkdir()
    monkeypatch.setattr(runner, "RESULTS", results)
    monkeypatch.setattr(runner, "SPOT", spot)
    monkeypatch.setattr(runner, "WINDOWS", {"toy": (start, last+DAY)})
    dates = pd.date_range(pd.Timestamp(start, unit="ms", tz="UTC"), pd.Timestamp(last, unit="ms", tz="UTC"))
    reference = pd.DataFrame({"timestamp": dates.strftime("%Y-%m-%dT00:00:00Z"), "strategy_nav": 100000.})
    for symbol in ("BTCUSDT", "ETHUSDT"):
        reference.to_csv(spot / f"{symbol}_toy.csv", index=False)
    write(results / "run_contract.json", {"synthetic": True})
    events = data.events_range(start, last)
    plan = {"2025-12-30": {} if all_cash else {"BTCUSDT": 1.}}
    first = runner.execute_case(data, events, plan, "toy", "lightgbm", 5)
    def no_rerun(*args, **kwargs):
        raise AssertionError("Verified completed cases must be reused")
    monkeypatch.setattr(runner, "simulate", no_rerun)
    second = runner.execute_case(data, events, plan, "toy", "lightgbm", 5)
    assert first == second and first["daily_observations"] == 8
    if all_cash:
        assert first["total_return"] == 0 and first["Sharpe_rf0"] is None
