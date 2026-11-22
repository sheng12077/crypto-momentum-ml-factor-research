"""Memory representation must preserve exact prices and repair conflict checks."""

import numpy as np
import pandas as pd
import pytest

from crypto_factor_research.window_data import TradeBars, WindowData


def test_compact_trade_lookup_matches_dictionary_without_per_bar_objects():
    size = 10000
    frame = pd.DataFrame(
        {
            "bar_open_ms": np.arange(size, dtype=np.int64) * 3600000,
            "close": np.arange(size, dtype=float) + 0.125,
            "volume": np.arange(size, dtype=float),
            "quote_volume": np.arange(size, dtype=float) * 2.5,
        }
    )
    bars = TradeBars(frame.iloc[::-1])
    reference = {
        int(r.bar_open_ms): (r.close, r.volume, r.quote_volume) for r in frame.itertuples()
    }
    for t in [0, 3600000, 50 * 3600000, (size - 1) * 3600000]:
        assert bars[t] == reference[t]
    assert bars.get(-1) is None and bars.get(1, "missing") == "missing"
    assert bars.stamps.nbytes + bars.values.nbytes == size * 32
    assert not bars.extra


def test_sparse_repairs_preserve_original_price_and_reject_conflicts():
    bars = TradeBars(
        pd.DataFrame({"bar_open_ms": [0], "close": [1.0], "volume": [2.0], "quote_volume": [3.0]})
    )
    bars[0] = (1.0, 2.0, 3.0)
    assert not bars.extra
    with pytest.raises(ValueError, match="Conflicting"):
        bars[0] = (2.0, 2.0, 3.0)
    bars[3600000] = (4.0, 5.0, 6.0)
    assert bars[3600000] == (4.0, 5.0, 6.0)
    with pytest.raises(KeyError):
        _ = bars[123]


def test_compact_lookup_rejects_duplicate_time():
    frame = pd.DataFrame(
        {
            "bar_open_ms": [0, 0],
            "close": [1.0, 1.0],
            "volume": [2.0, 2.0],
            "quote_volume": [3.0, 3.0],
        }
    )
    with pytest.raises(ValueError, match="Duplicate"):
        TradeBars(frame)


def test_zero_volume_is_still_not_a_fill_and_conflicting_recovery_fails():
    bars = pd.DataFrame(
        {
            "instrument_id": ["A", "A"],
            "bar_open_ms": [0, 3600000],
            "close": [1.0, 2.0],
            "volume": [0.0, 3.0],
            "quote_volume": [0.0, 9.0],
        }
    )
    data = WindowData(
        {"trade": bars, "mark": bars, "funding": pd.DataFrame(columns=["instrument_id"])}, {}
    )
    assert data.vwap("A", 0) is None
    assert data.vwap("A", 3600000) == 3.0
    with pytest.raises(ValueError, match="Conflicting"):
        data.add_bar(
            "A", "trade", {"bar_open_ms": 0, "close": 1.0, "volume": 1.0, "quote_volume": 1.0}
        )
