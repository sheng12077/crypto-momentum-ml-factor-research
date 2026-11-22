"""Self-contained synthetic cross-year accounting example; never reads local market data."""

import json
import tempfile
from pathlib import Path
from .settings import DAY, HOUR, ms
from .data.historical import ContinuousData
from .backtest.engine import simulate


def smoke():
    start, stop = ms("2022-12-30"), ms("2023-01-08")
    change = ms("2023-01-01")
    data = ContinuousData.__new__(ContinuousData)
    data.symbols, data.terminal_ends = ["BTCUSDT"], {}
    data.mark = lambda symbol, t: (100.0 if t < change else 110.0, t)
    data.vwap = lambda symbol, t: 100.0 if t < change else 110.0
    data.trades = {
        "BTCUSDT": {
            t: (100.0 if t < change else 110.0, 1.0, 100.0) for t in range(start, stop, HOUR)
        }
    }
    data.funding = {"BTCUSDT": [(ms("2022-12-31") + 8 * HOUR, 0.0001), (change, 0.0001)]}
    events = data.events_range(start, stop - DAY)
    plan = {"2022-12-30": {"BTCUSDT": 1.0}}
    with tempfile.TemporaryDirectory(prefix="momentum_synthetic_") as folder:
        _, result = simulate(data, events, plan, Path(folder), bps=0)
    if abs(result["ending_nav"] - 109874.0) > 0.00001:
        raise ValueError("Synthetic accounting example changed")
    out = {
        "success": True,
        "synthetic_only": True,
        "market_data_required": False,
        "ending_nav": result["ending_nav"],
        "financial_sha256": result["financial_sha256"],
    }
    print(json.dumps(out))
    return out
