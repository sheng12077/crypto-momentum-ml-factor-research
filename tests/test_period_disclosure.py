"""Publication must distinguish independent OOS cash from carry-over path slices."""

import numpy as np
import pandas as pd
import pytest
from momentum_data.reporting import publication as p


def fixture_frames():
    whole = pd.DataFrame(
        {n: [100.0, 110.0, 120.0, 130.0, 140.0, 150.0] for n in p.LABELS},
        index=pd.date_range("2024-12-30", periods=6, tz="UTC"),
    )
    oos = pd.DataFrame(
        {n: [100.0, 110.0, 95.0, 105.0] for n in p.LABELS},
        index=pd.date_range("2025-01-01", periods=4, tz="UTC"),
    )
    metrics, monthly = p.source.performance_tables(oos)
    return whole, oos, metrics, monthly


def test_original_account_and_full_path_slice_are_labeled_separately(tmp_path, monkeypatch):
    whole, oos, metrics, monthly = fixture_frames()
    monkeypatch.setattr(p, "ASSETS", tmp_path)
    monkeypatch.setattr(p, "ROOT", tmp_path)
    base = tmp_path / "frozen"
    case = base / "results/continuous/lightgbm/slippage_5bps"
    case.mkdir(parents=True)
    (case / "_complete.json").write_text("{}")
    monkeypatch.setattr(
        p, "original_oos", lambda: (base, {5: (oos, metrics, monthly), 10: (oos, metrics, monthly)})
    )
    full_metrics, _ = p.source.performance_tables(whole)
    brief, detail = p.period_disclosure(whole, full_metrics)
    assert "Original OOS account (2025--2026) | +5.00%" in brief
    assert "OOS-date slice of full path; carry-in diagnostic | +25.00%" in brief
    assert "Full path (2022--2026) | +50.00%" in brief
    assert "not a single model trained once" in detail
    assert (tmp_path / "full_period_vs_oos.png").exists()


def test_period_comparison_rejects_different_snapshot_dates(tmp_path, monkeypatch):
    whole, oos, metrics, monthly = fixture_frames()
    monkeypatch.setattr(
        p,
        "original_oos",
        lambda: (tmp_path, {5: (oos, metrics, monthly), 10: (oos, metrics, monthly)}),
    )
    full_metrics, _ = p.source.performance_tables(whole)
    with pytest.raises(ValueError, match="comparison dates differ"):
        p.period_disclosure(whole.iloc[:-1], full_metrics)
