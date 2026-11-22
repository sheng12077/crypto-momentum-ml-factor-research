"""Lifecycle-boundary regression tests, without historical performance or network."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from final_holdout_common import HOUR, ms
from final_holdout_engine import FinalHistoricalData, simulate
from final_holdout_lifecycle import filter_terminal_rows, inherit_source_caches, repair_pair
from test_final_holdout import synthetic_data


def test_retired_mark_tail_is_not_an_active_trade_gap(tmp_path):
    end = ms("2025-05-21T09:00:00")
    start = ms("2025-05-21")
    trade = [{"bar_open_ms": start+i*HOUR, "close": 1., "volume": 1. if i < 9 else 0.,
              "quote_volume": 1. if i < 9 else 0.} for i in range(10)]
    mark = [{"bar_open_ms": start+i*HOUR, "close": 1.} for i in range(24)]
    products, audit = filter_terminal_rows("EOSUSDT", {"trade": trade, "mark": mark, "funding": []},
                                           {"effective_ms": end})
    class NoRequests:
        def fetch(self, *args):
            raise AssertionError("Verified terminal tail must not trigger a download")
    t, m, changed, counts = repair_pair("EOSUSDT", products["trade"], products["mark"], NoRequests(), tmp_path)
    assert len(t) == len(m) == 9 and not changed and counts == {"trade": 0, "mark": 0}
    assert audit["quarantined"] == {"trade": 1, "mark": 15, "funding": 0}
    assert len(trade) == 10 and len(mark) == 24
    trade[-1]["volume"] = 1.  # Settlement prints in terminal bucket are still excluded.
    filtered, _ = filter_terminal_rows("EOSUSDT", {"trade": trade, "mark": mark}, {"effective_ms": end})
    assert len(filtered["trade"]) == 9
    trade.append({"bar_open_ms": end+HOUR, "close": 1., "volume": 1., "quote_volume": 1.})
    with pytest.raises(ValueError, match="episode review"):
        filter_terminal_rows("EOSUSDT", {"trade": trade, "mark": mark}, {"effective_ms": end})


def test_unproven_gap_still_fails_with_asset_kind_and_time(tmp_path):
    stamp = ms("2025-05-21")
    class EmptyArchive:
        def fetch(self, *args):
            return {}
    with pytest.raises(ValueError, match="EOSUSDT/trade/2025-05-21"):
        repair_pair("EOSUSDT", [], [{"bar_open_ms": stamp, "close": 1.}], EmptyArchive(), tmp_path)
    evidence = json.loads((tmp_path / "EOSUSDT_trade_2025-05-21_unresolved.json").read_text())
    assert evidence["unresolved_open_ms"] == [stamp]


def test_terminal_mark_is_not_usable_after_expiry():
    data = FinalHistoricalData.__new__(FinalHistoricalData)
    end = ms("2025-05-21T09:00:00")
    data.terminal_ends = {"EOSUSDT": end}
    data.marks = {"EOSUSDT": (np.array([end-HOUR, end, end+HOUR], dtype=np.int64), np.array([1., 1., 1.]))}
    assert data.mark("EOSUSDT", end-1) is not None
    assert data.mark("EOSUSDT", end) is None and data.mark("EOSUSDT", end+HOUR) is None


@pytest.mark.parametrize("held", [True, False])
def test_no_synthetic_settlement_for_held_terminal_contract(tmp_path, held):
    data, start, last = synthetic_data()
    data.terminal_ends = {"BTCUSDT": ms("2026-01-01")}
    plan = {"2025-12-30": {"BTCUSDT": 1.} if held else {}}
    events = data.events_range(start, last)
    assert len([e for e in events if e["kind"] == "terminal_boundary"]) == 1
    if held:
        with pytest.raises(ValueError, match="Unsupported terminal settlement held"):
            simulate(data, events, plan, tmp_path, bps=0)
        assert not (tmp_path / "engine_summary.json").exists()
    else:
        _, result = simulate(data, events, plan, tmp_path, bps=0)
        assert result["ending_nav"] == 100000.


def test_nonterminal_financial_behavior_is_identical(tmp_path):
    from first_development_engine import simulate as original
    data, start, last = synthetic_data()
    events, plan = data.events_range(start, last), {"2025-12-30": {"BTCUSDT": 1.}}
    _, before = original(data, events, plan, tmp_path / "original", bps=5)
    _, after = simulate(data, events, plan, tmp_path / "guarded", bps=5)
    assert before["financial_sha256"] == after["financial_sha256"]


def test_acquisition_cache_copy_preserves_request_budget_and_old_contract(tmp_path):
    old, new = tmp_path / "v20261122_001", tmp_path / "v20261122_002"
    (old / "repair/raw").mkdir(parents=True)
    (old / "repair/raw/budget.json").write_text('{"requests":2,"jobs":["trade/EOS/day"]}')
    (old / "code_contract.json").write_text('{"original":true}')
    inherit_source_caches(new)
    assert (new / "repair/raw/budget.json").read_bytes() == (old / "repair/raw/budget.json").read_bytes()
    assert (old / "code_contract.json").read_text() == '{"original":true}'
    assert not (new / "code_contract.json").exists()


def test_funding_execution_collision_uses_completed_mark_not_vwap(tmp_path):
    data, start, last = synthetic_data()
    funding_at = ms("2026-01-05")+2*HOUR
    original_vwap = data.vwap
    data.vwap = lambda symbol, t: 200. if t == funding_at-HOUR else original_vwap(symbol, t)
    data.funding = {"BTCUSDT": [(start+2*HOUR, .001), (funding_at, .001)]}
    events = data.events_range(start, last)
    collision = next(e for e in events if e["stamp"] == funding_at*1000000 and e["symbol"] == "BTCUSDT")
    assert collision["kind"] == "execution" and collision["mark_at"] is None
    assert collision["price"] == 200. and collision["funding_price"] == 110.
    _, result = simulate(data, events, {"2025-12-30": {"BTCUSDT": 1.}}, tmp_path, bps=0)
    ledger = pd.read_csv(tmp_path / "funding.csv")
    assert len(ledger) == 1 and ledger.mark_proxy.iloc[0] == 110.
    assert ledger.signed_quantity.iloc[0] == 1000. and ledger.cashflow_usdt.iloc[0] == -110.
    assert result["ending_nav"] == pytest.approx(109785.)


def test_terminal_blocker_is_reported_without_changing_selection():
    from run_final_holdout_cases import terminal_blockers
    portfolio = {"2025-05-12": {"EOSUSDT": .1}}
    boundary = {"EOSUSDT": {"effective_ms": ms("2025-05-21T09:00:00"), "source_url": "official"}}
    blocked = terminal_blockers(portfolio, "2025", boundary)
    assert blocked[0]["instrument_id"] == "EOSUSDT" and blocked[0]["target_weight"] == .1
    assert portfolio == {"2025-05-12": {"EOSUSDT": .1}}
    assert terminal_blockers(portfolio, "2026_partial", boundary) == []


def test_missing_control_gate_is_unknown_not_false_or_passed():
    from run_final_holdout_cases import gates
    rows = []
    for name in ("2025", "2026_partial", "continuous"):
        for bps in (5, 10):
            rows.append({"window": name, "model": "lightgbm", "slippage_bps": bps, "total_return": .1, "Sharpe_rf0": 1.})
            if name == "2026_partial":
                rows.append({"window": name, "model": "momentum60", "slippage_bps": bps, "total_return": .05, "Sharpe_rf0": .5})
    result = gates(pd.DataFrame(rows))
    assert result["2025"]["beats_matched_momentum_return_and_sharpe"] is None
    assert result["continuous"]["beats_matched_momentum_return_and_sharpe"] is None
    assert result["2026_partial"]["beats_matched_momentum_return_and_sharpe"] is True
