"""Small checks of the next unchanged validation window; no historical fitting."""

import json
from pathlib import Path

import pandas as pd

from crypto_factor_research.config import DAY
from crypto_factor_research.first_window import ranked_schedule, training_rows
from crypto_factor_research.window_data import ms, window_label

ROOT = Path(__file__).resolve().parents[1]


def test_2024_changes_only_dates_output_sources_and_registration():
    prior = json.loads((ROOT / "config/dynamic_2023.json").read_text())
    current = json.loads((ROOT / "config/dynamic_2024.json").read_text())
    allowed = {
        "spot_root", "output_root", "train_stop", "start", "stop_exclusive",
        "registration", "cessation_notices",
    }
    assert {k: v for k, v in prior.items() if k not in allowed} == {
        k: v for k, v in current.items() if k not in allowed
    }
    assert current["train_stop"] == current["start"] == "2024-01-01"
    assert current["stop_exclusive"] == "2025-01-01"
    assert window_label(current) == "train2021-2023/trade2024"
    assert len({x["symbol"] for x in current["cessation_notices"]}) == len(
        current["cessation_notices"]
    )


def test_2024_schedule_starts_on_january_first_monday():
    frame = pd.DataFrame({
        "instrument_id": [f"A{i:02}" for i in range(20)],
        "feature_cutoff_ms": ms("2024-01-01"), "score": range(20),
    })
    schedule = ranked_schedule(frame, 2024, weeks=2)
    assert len(schedule) == 27
    assert list(schedule)[0] == "2024-01-01"
    assert list(schedule)[-1] == "2024-12-30"


def test_labels_maturing_in_2024_are_excluded():
    class Data:
        notices = {}

        def vwap(self, symbol, t):
            assert t < ms("2024-01-01"), "Training must not read 2024 prices"
            return 100 + t / DAY

    cutoff = ms("2024-01-01")
    frame = pd.DataFrame({
        "instrument_id": ["A", "A"],
        "feature_cutoff_ms": [cutoff - 10 * DAY, cutoff - 2 * DAY],
    })
    train, _ = training_rows(frame, Data(), cutoff)
    assert len(train) == 1
    assert train.feature_cutoff_ms.iloc[0] == cutoff - 10 * DAY
