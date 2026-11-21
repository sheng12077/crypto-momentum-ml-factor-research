import json

import numpy as np
import pandas as pd
import pytest

from momentum_data.backtest_analysis import (
    load_development_run,
    performance_tables,
    plot_development,
    validate_daily,
)


def fixture_daily():
    return pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=4, tz="UTC"),
        "strategy_nav": [100, 110, 99, 108.9], "btc_nav": [100, 100, 100, 100],
        "eth_nav": [100, 105, 100, 110], "commissions_usdt": [0, 1, 1, 1],
        "funding_cashflow_usdt": [0, -0.1, 0.1, 0], "traded_notional_usdt": [0, 10, 10, 10],
        "gross_exposure": [0, 1, 1, 0], "net_exposure": [0, 0, 0, 0],
    })


def test_metrics_known_drawdown_and_monthly_compounding():
    metrics, monthly = performance_tables(validate_daily(fixture_daily()))
    assert metrics.loc["strategy_nav", "total_return"] == pytest.approx(0.089)
    assert metrics.loc["strategy_nav", "MDD"] == pytest.approx(-0.1)
    assert monthly.strategy_nav.iloc[0] == pytest.approx(0.089)
    assert np.isnan(metrics.loc["btc_nav", "Sharpe_rf0"])
    assert np.isnan(metrics.loc["btc_nav", "Calmar"])


@pytest.mark.parametrize("failure", ["gap", "duplicate", "nan", "bankrupt", "exposure"])
def test_bad_inputs_are_not_silently_filled(failure):
    data = fixture_daily()
    if failure == "gap":
        data = data.drop(index=1)
    elif failure == "duplicate":
        data.loc[1, "timestamp"] = data.loc[0, "timestamp"]
    elif failure == "nan":
        data.loc[1, "strategy_nav"] = np.nan
    elif failure == "bankrupt":
        data.loc[1, "strategy_nav"] = 0
    else:
        data.loc[1, "net_exposure"] = 2
    with pytest.raises(ValueError):
        validate_daily(data)


def manifest():
    return {"report_type": "historical_development", "OOS_performance_inspected": False,
            "start_inclusive": "2021-01-01T00:00:00Z",
            "end_exclusive": "2023-01-01T00:00:00Z", "currency": "USDT",
            "external_cashflows": "none",
            "nav_basis": "marked_equity_net_of_fees_and_funding"}


def test_approved_development_contract(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(manifest()))
    fixture_daily().to_csv(tmp_path / "daily.csv", index=False)
    daily, _ = load_development_run(tmp_path)
    assert len(daily) == 4


def test_oos_manifest_rejected_before_opening_any_csv(tmp_path):
    meta = manifest()
    meta.update(start_inclusive="2025-01-01T00:00:00Z", end_exclusive="2026-01-01T00:00:00Z")
    (tmp_path / "manifest.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="2021-2022"):
        load_development_run(tmp_path)


def test_out_of_bounds_csv_rejected_in_timestamp_only_pass(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(manifest()))
    # No NAV columns: demonstrates that the loader refuses dates before reading NAV.
    pd.DataFrame({"timestamp": ["2025-01-01T00:00:00Z"]}).to_csv(
        tmp_path / "daily.csv", index=False)
    with pytest.raises(ValueError, match="dates exceed"):
        load_development_run(tmp_path)


def test_dashboard_renders_from_test_fixture_only(tmp_path):
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, _, _ = plot_development(validate_daily(fixture_daily()))
    fig.suptitle("TEST FIXTURE — not actual strategy performance")
    assert len(fig.axes) == 6
    fig.savefig(tmp_path / "fixture_dashboard.png", dpi=80)
    plt.close(fig)
