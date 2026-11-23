"""Large low-price positions must close in exact filled units and reconcile cash."""

import csv
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from crypto_factor_research.config import HOUR
from crypto_factor_research.window_audit import Oracle, audit_case, audit_quantity_normalizations
from crypto_factor_research.window_data import WindowData, ms


def test_large_quantities_partial_rebalance_and_flips_close_and_reconcile(tmp_path):
    from crypto_factor_research.execution import simulate

    start, last = ms("2025-01-06"), ms("2025-01-11")
    stamps = np.arange(start - HOUR, last + HOUR, HOUR, dtype=np.int64)
    market = {}
    bars = pd.DataFrame(
        {
            "instrument_id": "BTCUSDT",
            "bar_open_ms": stamps,
            "close": 0.00015,
            "volume": 1000000.0,
            "quote_volume": 150.0,
        }
    )
    market["trade"] = market["mark"] = bars
    market["funding"] = pd.DataFrame(
        columns=["instrument_id", "event_timestamp_ms", "funding_rate", "funding_interval_hours"]
    )
    data = WindowData(market, {})
    schedule = {
        "2025-01-06": {"BTCUSDT": 0.1},
        "2025-01-07": {"BTCUSDT": 0.08},
        "2025-01-08": {"BTCUSDT": -0.04},
        "2025-01-09": {"BTCUSDT": 0.03},
    }
    events = data.events(start, last, {ms(d) for d in schedule})
    folder = tmp_path / "results/large_20bps"
    _, result = simulate(data, events, schedule, folder, bps=20, exact_execution=True)
    assert result["success"] and result["exact_execution"]
    assert result["native_quantity_normalizations"] >= 1
    fills = list(csv.DictReader((folder / "fills.csv").open()))
    signed = sum(
        (Decimal(r["quantity"]) * (1 if r["side"] == "BUY" else -1) for r in fills), Decimal(0)
    )
    assert signed == 0
    assert max(Decimal(r["quantity"]) for r in fills) > Decimal("50000000")
    for kind, frame in market.items():
        frame.to_parquet(tmp_path / (kind + ".parquet"), index=False)
    (tmp_path / "notices.json").write_text("{}")
    case = {"case": "large", "bps": 20}
    assert audit_case(tmp_path, case, Oracle(tmp_path, [case]), start, last)["success"]


def test_numerical_normalization_must_not_erase_even_tiny_real_exposure(tmp_path):
    fills = [
        {
            "instrument_id": "A",
            "timestamp_ns": "100",
            "quantity": "0.00000001",
            "side": "BUY",
            "price": "0.0001",
        }
    ]
    pd.DataFrame(
        [
            {
                "timestamp_ns": 101,
                "instrument_id": "A",
                "fills_seen": 1,
                "native_signed_quantity": "0.00000001",
                "exact_signed_quantity": "0",
                "notional_usdt": "0.000000000001",
                "cash_adjustment_usdt": "0",
            }
        ]
    ).to_csv(
        tmp_path / "quantity_normalizations.csv",
        index=False,
    )
    with pytest.raises(ValueError, match="not numerically flat"):
        audit_quantity_normalizations(tmp_path, fills)


def test_exact_engine_replay_is_identical_for_large_quantities(tmp_path):
    from crypto_factor_research.execution import simulate

    start, last = ms("2025-01-06"), ms("2025-01-08")
    stamps = np.arange(start - HOUR, last + HOUR, HOUR, dtype=np.int64)
    bars = pd.DataFrame(
        {
            "instrument_id": "BTCUSDT",
            "bar_open_ms": stamps,
            "close": 0.000219,
            "volume": 1000000.0,
            "quote_volume": 219.0,
        }
    )
    market = {"trade": bars, "mark": bars, "funding": pd.DataFrame(columns=["instrument_id"])}
    hashes = []
    for n in range(2):
        data = WindowData(market, {})
        _, summary = simulate(
            data,
            data.events(start, last, {start}),
            {"2025-01-06": {"BTCUSDT": 0.1}},
            tmp_path / str(n),
            bps=5,
            exact_execution=True,
        )
        hashes.append(summary["financial_sha256"])
    assert hashes[0] == hashes[1]
