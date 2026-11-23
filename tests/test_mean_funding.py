"""Declared accounting estimates stay out of predictors and are independently audited."""

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from crypto_factor_research.config import DAY, HOUR, sha
from crypto_factor_research.mean_funding_window import apply_assumptions, main_stage, mean_records
from crypto_factor_research.window_audit import Oracle, audit_case
from crypto_factor_research.window_data import WindowData, ms

ROOT = Path(__file__).resolve().parents[1]
START = ms("2026-06-24")
POLICY = {
    "method": "adjacent_mean",
    "use": "accounting_only",
    "uses_future_anchor": True,
    "start_utc": "2026-06-24",
    "stop_exclusive_utc": "2026-06-25",
}


def fixture_data():
    return SimpleNamespace(
        funding={"A": [(START + 5, -0.001), (START + 8 * HOUR + 6, 0.003)]},
        funding_meta={"A": [(START + 5, 4.0), (START + 8 * HOUR + 6, 4.0)]},
    )


def test_mean_is_per_contract_and_only_in_registered_gap():
    data = fixture_data()
    rows = mean_records(data, START, START + DAY)
    assert len(rows) == 1 and rows[0]["timestamp_ms"] == START + 4 * HOUR
    assert rows[0]["rate"] == pytest.approx(0.001)
    assert len(data.funding["A"]) == 2
    assert mean_records(data, START + DAY, START + 2 * DAY) == []
    data.funding_meta["A"][-1] = (START + 8 * HOUR + 6, 8.0)
    assert mean_records(data, START, START + DAY) == []


def test_scenario_config_preserves_strategy_and_strict_config():
    strict = json.loads((ROOT / "config/dynamic_2026.json").read_text())
    scenario = json.loads((ROOT / "config/dynamic_2026_mean_funding.json").read_text())
    allowed = {"output_root", "registration", "funding_imputation"}
    assert {k: v for k, v in strict.items() if k not in allowed} == {
        k: v for k, v in scenario.items() if k not in allowed
    }
    assert "funding_imputation" not in strict
    assert scenario["funding_imputation"] == POLICY


def test_all_missing_slots_use_original_anchor_mean():
    data = fixture_data()
    data.funding["A"][-1] = (START + 12 * HOUR, 0.003)
    data.funding_meta["A"][-1] = (START + 12 * HOUR, 4.0)
    rows = mean_records(data, START, START + DAY)
    assert [r["timestamp_ms"] for r in rows] == [START + 4 * HOUR, START + 8 * HOUR]
    assert all(r["rate"] == pytest.approx(0.001) for r in rows)


def test_raw_funding_is_preserved_and_tampered_estimate_is_rejected(tmp_path):
    (tmp_path / "funding.parquet").write_bytes(b"original funding fixture")
    digest = sha(tmp_path / "funding.parquet")
    saved = apply_assumptions(tmp_path, {"funding_imputation": POLICY}, fixture_data())
    assert sha(tmp_path / "funding.parquet") == digest
    assert saved["uses_future_anchor"] and saved["estimated_events"] == 1
    saved["records"][0]["rate"] = 0.9
    (tmp_path / "funding_assumptions.json").write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="do not overwrite"):
        apply_assumptions(tmp_path, {"funding_imputation": POLICY}, fixture_data())


def test_fit_observes_original_rates_before_accounting_overlay(tmp_path, monkeypatch):
    from crypto_factor_research import first_window as core

    config = {
        "funding_imputation": POLICY,
        "train_stop": "2026-01-01",
        "start": "2026-01-01",
        "output_root": "output",
    }
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(config))
    data, calls = fixture_data(), []
    monkeypatch.setattr(core, "identity", lambda *args: {"fixture": True})

    def prepare(root, config, path, identity):
        path.mkdir(parents=True)
        (path / "funding.parquet").write_bytes(b"fixture")

    def fit(*args):
        assert len(data.funding["A"]) == 2
        calls.append("fit_original")

    def preflight(*args):
        assert len(data.funding["A"]) == 3
        calls.append("preflight_estimates")
        return {"success": False, "source_bindings": {}}

    monkeypatch.setattr(core, "prepare", prepare)
    monkeypatch.setattr(core, "load_data", lambda path: data)
    monkeypatch.setattr(core, "fit", fit)
    monkeypatch.setattr(core, "preflight", preflight)
    assert not main_stage(tmp_path, cfg, "all")["success"]
    assert calls == ["fit_original", "preflight_estimates"]


def test_batch_selects_strict_2025_and_mean_2026(tmp_path):
    batch = runpy.run_path(str(ROOT / "scripts/run_dynamic_final_windows.py"))["run_batch"]
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    assert batch(root=tmp_path, runner=runner, funding_assumption="adjacent-mean")["success"]
    assert calls[0][3] == "window" and calls[1][3] == "window-mean"
    assert calls[1][5].endswith("2026_mean_funding.json")
    assert not (tmp_path / "data/processed/dynamic_final_windows/batch_status.json").exists()


def test_actual_tiny_engine_pays_estimated_funding_and_independent_audit_checks_it(tmp_path):
    from momentum_data.backtest.engine import simulate

    start, last = START - DAY, START + DAY
    stamps = np.arange(start - HOUR, last + HOUR, HOUR, dtype=np.int64)
    bars = pd.DataFrame(
        {
            "instrument_id": "BTCUSDT",
            "bar_open_ms": stamps,
            "close": 100.0,
            "volume": 100.0,
            "quote_volume": 10000.0,
        }
    )
    funding = pd.DataFrame(
        {
            "instrument_id": ["BTCUSDT", "BTCUSDT"],
            "event_timestamp_ms": [START, START + 8 * HOUR],
            "funding_rate": [0.001, 0.003],
            "funding_interval_hours": [4.0, 4.0],
        }
    )
    market = {"trade": bars, "mark": bars, "funding": funding}
    for kind, frame in market.items():
        frame.to_parquet(tmp_path / (kind + ".parquet"), index=False)
    (tmp_path / "notices.json").write_text("{}")
    data = WindowData(market, {})
    config = {"funding_imputation": POLICY}
    apply_assumptions(tmp_path, config, data)
    assumption = tmp_path / "funding_assumptions.json"
    (tmp_path / "preflight.json").write_text(
        json.dumps(
            {
                "source_bindings": {str(assumption.resolve()): sha(assumption)},
            }
        )
    )
    folder = tmp_path / "results/lightgbm_0bps"
    _, result = simulate(
        data, data.events(start, last, {start}), {"2026-06-23": {"BTCUSDT": 0.1}}, folder, bps=0
    )
    assert result["success"]
    paid = pd.read_csv(folder / "funding.csv")
    assert len(paid) == 3 and paid.cashflow_usdt.sum() == pytest.approx(-60.0)
    case = {"case": "lightgbm", "bps": 0}
    oracle = Oracle(tmp_path, [case])
    assert oracle.add_mean_assumptions(config, tmp_path) == 1
    assert audit_case(tmp_path, case, oracle, start, last)["success"]
    # Even rehashing a falsified mean must not evade the independent anchor check.
    payload = json.loads(assumption.read_text())
    payload["records"][0]["rate"] = 0.02
    assumption.write_text(json.dumps(payload))
    (tmp_path / "preflight.json").write_text(
        json.dumps(
            {
                "source_bindings": {str(assumption.resolve()): sha(assumption)},
            }
        )
    )
    with pytest.raises(ValueError, match="anchor/rate mismatch"):
        Oracle(tmp_path, [case]).add_mean_assumptions(config, tmp_path)
