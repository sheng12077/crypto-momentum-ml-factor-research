import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_validation_2024 import assert_training_samples


def test_saved_training_ignores_only_parquet_index_loss(tmp_path):
    expected = pd.DataFrame({"instrument_id": ["BTCUSDT", "ETHUSDT"],
                             "label": [.1, -.2]}, index=[0, 37])
    path = tmp_path / "training.parquet"
    expected.to_parquet(path, index=False)
    saved = pd.read_parquet(path)
    assert_training_samples(saved, expected)
    changed = saved.copy()
    changed.loc[0, "label"] += 1e-12
    with pytest.raises(AssertionError):
        assert_training_samples(changed, expected)
    with pytest.raises(AssertionError):
        assert_training_samples(saved.iloc[::-1], expected)
    with pytest.raises(AssertionError):
        assert_training_samples(saved.iloc[:1], expected)
