"""The named frozen run, separate from implementation and local data location."""

import json
import pandas as pd
from .paths import ROOT, DATA_ROOT, LEGACY

CONFIG = json.loads((ROOT / "config/continuous.json").read_text())
DAY, HOUR = 86400000, 3600000
FEATURES = CONFIG["features"]


def ms(value):
    return int(pd.Timestamp(value, tz="UTC").timestamp() * 1000)


START, STOP = ms(CONFIG["start"]), ms(CONFIG["stop_exclusive"])
YEARS = tuple(range(2022, 2027))
PREPARED = DATA_ROOT / CONFIG["prepared"]
BASE = DATA_ROOT / CONFIG["frozen_output"]
PACKAGE_OUTPUT = DATA_ROOT / CONFIG["package_output"]
MODEL_ROOTS = {
    2022: DATA_ROOT / "interim/first_development/v20261121_001/results_v003/model",
    2023: DATA_ROOT / "interim/validation_2023/v20261121_001/results/model",
    2024: DATA_ROOT / "interim/validation_2024/v20261121_002/results/model",
    2025: PREPARED.parent / "results/models/2025",
    2026: PREPARED.parent / "results/models/2026",
}
TRAINING_PREPARED = {
    y: MODEL_ROOTS[y].parents[1] / ("prepared_v003" if y == 2022 else "prepared")
    for y in (2022, 2023, 2024)
}
