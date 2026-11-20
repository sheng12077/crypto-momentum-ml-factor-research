"""Integration tests run in the isolated Linux runtime; no historical data access."""

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("nautilus_trader")
_path = Path(__file__).resolve().parents[1] / "scripts/run_nautilus_smoke.py"
_spec = importlib.util.spec_from_file_location("nautilus_smoke", _path)
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)


def test_accounting_suite_and_determinism():
    first = smoke.suite()
    assert first == smoke.suite()
    cases = {case["name"]: case for case in first}
    assert Decimal(cases["rising_roundtrip"]["actual_net_usdt"]) == Decimal("89.95")
    assert Decimal(cases["flat_roundtrip"]["actual_net_usdt"]) == Decimal("-10")
    profits = [Decimal(cases[f"slippage_{bps}bps"]["actual_net_usdt"])
               for bps in (0, 2, 5, 10)]
    assert all(left > right for left, right in zip(profits, profits[1:], strict=False))


def test_skipped_funding_event_fails_instead_of_using_later_position():
    with pytest.raises(RuntimeError, match="Skipped funding timestamp"):
        smoke.run_case(name="missing_event", funding=True, omit_funding_tick=True)
