"""Hand-computed reversal ledger and corruption detection for attribution."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import attribute_validation_2024 as attribution  # noqa: E402


@pytest.mark.parametrize("position,delta,expected", [
    (2, -3, [("long", 2/3), ("short", 1/3)]),
    (-2, 3, [("short", 2/3), ("long", 1/3)]),
    (2, -1, [("long", 1.)]), (0, -2, [("short", 1.)]),
])
def test_fee_allocation_handles_reversals(position, delta, expected):
    actual = attribution.fee_sides(position, delta)
    assert [v[0] for v in actual] == [v[0] for v in expected]
    assert [v[1] for v in actual] == pytest.approx([v[1] for v in expected])


def test_hand_computed_marked_reversal_ledger_and_corruption(tmp_path, monkeypatch):
    source, prepared, out = (tmp_path / name for name in ("source", "prepared", "out"))
    source.mkdir()
    prepared.mkdir()
    monkeypatch.setattr(attribution, "ROOT", tmp_path)
    monkeypatch.setattr(attribution, "BASE", tmp_path)
    monkeypatch.setattr(attribution, "SOURCE", source)
    monkeypatch.setattr(attribution, "OUT", out)
    monkeypatch.setattr(attribution, "plot_attribution", lambda *_: None)

    def ns(value):
        return pd.Timestamp(value, tz="UTC").value

    trade_times = ["2024-01-01 02:00", "2024-01-02 02:00", "2024-01-02 23:00"]
    prices, quantities, sides = [100.05, 119.94, 110.055], [2., 3., 1.], ["BUY", "SELL", "BUY"]
    fees = [p*q*.0005 for p, q in zip(prices, quantities, strict=True)]
    notionals = [p*q for p, q in zip(prices, quantities, strict=True)]
    pd.DataFrame({"timestamp_ns": [ns(v) for v in trade_times], "instrument_id": "BTCUSDT",
                  "side": sides, "quantity": quantities, "price": prices,
                  "commission_usdt": fees, "notional_usdt": notionals}).to_csv(source / "fills.csv", index=False)
    pd.DataFrame({"timestamp_ns": [ns("2024-01-01 08:00"), ns("2024-01-02 08:00")],
                  "instrument_id": "BTCUSDT", "signed_quantity": [2., -1.],
                  "cashflow_usdt": [1., -2.]}).to_csv(source / "funding.csv", index=False)
    day1 = 2*(110 - 100.05) + 1 - fees[0]
    day2 = 2*(119.94 - 110) + (119.94 - 110.055) - 2 - sum(fees[1:])
    frame = pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z", "2024-01-03T00:00:00Z"],
                          "strategy_nav": [100000., 100000+day1, 100000+day1+day2],
                          "commissions_usdt": [0., fees[0], sum(fees[1:])],
                          "funding_cashflow_usdt": [0., 1., -2.],
                          "traded_notional_usdt": [0., notionals[0], sum(notionals[1:])]})
    frame.to_csv(source / "daily.csv", index=False)
    pd.DataFrame({"month": ["2024-01-31"], "strategy_nav": [(day1+day2)/100000]}).to_csv(
        source / "monthly_returns.csv", index=False)
    pd.DataFrame({"instrument_id": ["BTCUSDT"], "bar_open_ms": [ns("2024-01-01 23:00") // 1_000_000],
                  "close": [110.]}).to_parquet(prepared / "mark.parquet")
    pd.DataFrame({"instrument_id": "BTCUSDT", "bar_open_ms": [ns(v)//1_000_000 - 3_600_000 for v in trade_times],
                  "volume": 1., "quote_volume": [100., 120., 110.]}).to_parquet(prepared / "trade.parquet")
    attribution.attribute()
    result = json.loads((out / "summary.json").read_text())
    assert result["annual"]["net_pnl"] == pytest.approx(day1 + day2)
    assert result["annual_side"]["long"]["price_pnl"] == pytest.approx(39.78)
    assert result["annual_side"]["short"]["price_pnl"] == pytest.approx(9.885)
    assert result["annual"]["slippage_proxy"] == pytest.approx(.335)
    frame.loc[2, "strategy_nav"] += .02
    frame.to_csv(source / "daily.csv", index=False)
    with pytest.raises(ValueError, match="NAV attribution mismatch"):
        attribution.attribute()
