import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_first_development import DAY, HOUR, funding_feature  # noqa: E402


def test_funding_feature_does_not_see_unpublished_or_future_event():
    cutoff = 1641168000000
    events = [{"event_timestamp_ms": cutoff - 7 * DAY + i * 8 * HOUR,
               "funding_rate": .0001, "funding_interval_hours": 8} for i in range(21)]
    expected = funding_feature(events, cutoff)
    events += [{"event_timestamp_ms": cutoff - 1000, "funding_rate": 999., "funding_interval_hours": 8},
               {"event_timestamp_ms": cutoff + DAY, "funding_rate": 999., "funding_interval_hours": 8}]
    assert funding_feature(events, cutoff) == pytest.approx(expected)
    assert expected == pytest.approx(.0021)
    assert funding_feature(events[1:], cutoff) is None


def test_engine_roundtrip_with_funding_and_known_quantity(tmp_path):
    pytest.importorskip("nautilus_trader")
    from first_development_engine import simulate

    start = 1640995200000
    asset = "BTCUSDT"
    data = SimpleNamespace(symbols=[asset], trades={asset: {start: (10000., 10., 100000.)}})
    events = []

    def add(ms, kind, price, mark_at=None, extra_ns=0, rate=None):
        events.append({"symbol": asset, "stamp": ms * 1000000 + extra_ns, "kind": kind,
                       "price": price, "mark_at": mark_at, "rate": rate})

    add(start, "mark", 10000., start)
    add(start, "snapshot", 10000., extra_ns=100)
    add(start + HOUR, "reference", 10000., start + HOUR)
    add(start + HOUR, "decision", 10000., extra_ns=100)
    add(start + 2 * HOUR, "execution", 10000.)
    add(start + 2 * HOUR, "check", 10000., extra_ns=100)
    add(start + 8 * HOUR, "funding", 10000., start + 8 * HOUR, rate=.001)
    add(start + DAY, "mark", 10100., start + DAY)
    add(start + DAY, "final", 10100., extra_ns=1)
    add(start + DAY, "final_check", 10100., extra_ns=2)
    add(start + DAY, "snapshot", 10100., extra_ns=100)
    _, result = simulate(data, events, {date(2022, 1, 1).isoformat(): {asset: .1}}, tmp_path, bps=0)
    assert result["ending_nav"] == pytest.approx(100079.95, abs=.01)
    assert result["fill_count"] == 2 and result["funding_cashflows"] == 1
    fills = pd.read_csv(tmp_path / "fills.csv")
    assert fills.quantity.iloc[0] == 1
