"""Fixed-unit spot holding arithmetic and timestamp normalization."""

from datetime import UTC, datetime
import pandas as pd
from ..settings import DAY, HOUR


def normalize_row(raw):
    row = list(raw)
    unit = "us" if int(row[0]) >= 100_000_000_000_000 else "ms"
    divisor = 1000 if unit == "us" else 1
    if int(row[0]) % divisor:
        raise ValueError("Open timestamp not millisecond aligned")
    row[0], row[6] = str(int(row[0]) // divisor), str(int(row[6]) // divisor)
    return row, unit


def benchmark(observed, start, stop):
    last, final = stop - DAY, stop - DAY - HOUR
    entry, exit_row = observed[start + HOUR], observed[final - HOUR]
    if entry["volume"] <= 0 or exit_row["volume"] <= 0:
        raise ValueError("Missing spot execution volume")
    buy, sell = (
        entry["quote"] / entry["volume"] * 1.0005,
        exit_row["quote"] / exit_row["volume"] * 0.9995,
    )
    units = 100000 / (buy * 1.001)
    cash = units * sell * 0.999
    rows = [
        {
            "timestamp": datetime.fromtimestamp(t / 1000, UTC).strftime("%Y-%m-%dT00:00:00Z"),
            "strategy_nav": 100000.0
            if t == start
            else cash
            if t > final
            else units * observed[t - HOUR]["close"],
        }
        for t in range(start, last + 1, DAY)
    ]
    return pd.DataFrame(rows), {
        "entry_fill": buy,
        "exit_fill": sell,
        "fixed_units": units,
        "entry_fee": units * buy * 0.001,
        "exit_fee": units * sell * 0.001,
        "final_nav": cash,
    }
