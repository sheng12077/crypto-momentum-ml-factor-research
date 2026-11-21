"""Read-only analysis of saved simulation outputs, separate from trading logic."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

NAV_COLUMNS = ["strategy_nav", "btc_nav", "eth_nav"]
FLOW_COLUMNS = ["commissions_usdt", "funding_cashflow_usdt", "traded_notional_usdt"]


def smoke_tables(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not report.get("synthetic_backtest_executed"):
        raise ValueError("Expected a synthetic accounting report")
    rows, fills = [], []
    for case in report["cases"]:
        rows.append({
            "scenario": case["name"], "passed": case["passed"],
            "net_usdt": float(case["actual_net_usdt"]),
            "expected_usdt": float(case["expected_net_usdt"]),
            "commission_usdt": sum(float(f["commission"]) for f in case["fills"]),
            "funding_usdt": sum(map(float, case["funding_cashflows_usdt"])),
            "slippage_bps": case["extra_slippage_bps_per_fill"],
        })
        fills.extend({"scenario": case["name"], **fill} for fill in case["fills"])
    summary = pd.DataFrame(rows).set_index("scenario")
    summary["reconciliation_error_usdt"] = summary.net_usdt - summary.expected_usdt
    return summary, pd.DataFrame(fills), report


def validate_daily(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["timestamp", *NAV_COLUMNS, *FLOW_COLUMNS, "gross_exposure", "net_exposure"]
    if missing := set(required) - set(frame):
        raise ValueError(f"Missing daily columns: {sorted(missing)}")
    data = frame[required].copy()
    data["timestamp"] = pd.to_datetime(data.timestamp, utc=True, errors="raise")
    index = pd.DatetimeIndex(data.pop("timestamp"))
    if len(index) < 2 or index.hasnans or not index.is_unique or not index.is_monotonic_increasing:
        raise ValueError("Daily NAV requires >=2 unique, increasing timestamps")
    if not (index == index.normalize()).all():
        raise ValueError("Require fixed 00:00 UTC daily snapshots")
    if not (index.to_series().diff().dropna() == pd.Timedelta(days=1)).all():
        raise ValueError("Missing daily snapshots; do not forward-fill returns")
    data.index = index
    data = data.apply(pd.to_numeric, errors="raise")
    if not np.isfinite(data.to_numpy(dtype=float)).all():
        raise ValueError("Missing/non-finite observations")
    if (data[NAV_COLUMNS] <= 0).any().any():
        raise ValueError("Nonpositive NAV: insolvency requires separate failure analysis")
    if (data[["commissions_usdt", "traded_notional_usdt", "gross_exposure"]] < 0).any().any():
        raise ValueError("Costs/notional/gross exposure cannot be negative")
    if (data.net_exposure.abs() > data.gross_exposure + 1e-10).any():
        raise ValueError("Absolute net exposure cannot exceed gross exposure")
    if (data[FLOW_COLUMNS].iloc[0] != 0).any():
        raise ValueError("Initial NAV row must have zero interval flows")
    return data


def load_development_run(directory: Path) -> tuple[pd.DataFrame, dict]:
    """Check permissions before opening the NAV file; never inspect OOS performance."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("report_type") != "historical_development":
        raise ValueError("Only historical_development reports are allowed")
    if manifest.get("OOS_performance_inspected") is not False:
        raise ValueError("Run must explicitly declare OOS_performance_inspected=false")
    start = pd.Timestamp(manifest["start_inclusive"])
    stop = pd.Timestamp(manifest["end_exclusive"])
    if start.tzinfo is None or stop.tzinfo is None:
        raise ValueError("Manifest bounds must include UTC timezone")
    if not (pd.Timestamp("2021-01-01", tz="UTC") <= start < stop
            <= pd.Timestamp("2023-01-01", tz="UTC")):
        raise ValueError("Notebook permits only 2021-2022 development data")
    if manifest.get("nav_basis") != "marked_equity_net_of_fees_and_funding":
        raise ValueError("NAV must include unrealized PnL, fees and funding")
    if manifest.get("external_cashflows") != "none" or manifest.get("currency") != "USDT":
        raise ValueError("Require no external cashflows and common USDT valuation")
    # Timestamp-only pass rejects mixed/OOS files before loading their NAV columns.
    dates = pd.to_datetime(pd.read_csv(directory / "daily.csv", usecols=["timestamp"])
                           .timestamp, utc=True, errors="raise")
    if not ((dates >= start) & (dates < stop)).all():
        raise ValueError("CSV dates exceed the permitted run interval")
    return validate_daily(pd.read_csv(directory / "daily.csv")), manifest


def performance_tables(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """365-day crypto annualization; sample volatility; zero-risk-free Sharpe.

    Returns and all benchmarks share the exact daily grid. Undefined zero-volatility
    Sharpe and zero-drawdown Calmar are NaN rather than misleading infinities.
    """
    nav = daily[NAV_COLUMNS]
    returns = nav.pct_change(fill_method=None).iloc[1:]
    rows = []
    for column in NAV_COLUMNS:
        r = returns[column]
        total = nav[column].iloc[-1] / nav[column].iloc[0] - 1
        cagr = (1 + total) ** (365 / len(r)) - 1
        vol = r.std(ddof=1) * np.sqrt(365)
        mdd = (nav[column] / nav[column].cummax() - 1).min()
        rows.append({
            "series": column, "total_return": total, "CAGR": cagr,
            "annualized_volatility": vol,
            "Sharpe_rf0": r.mean() * 365 / vol if vol > 0 else np.nan,
            "MDD": mdd, "Calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
            "daily_observations": len(r),
        })
    monthly = (1 + returns).resample(pd.offsets.MonthEnd()).prod() - 1
    monthly.index.name = "month_end_UTC_partial_months_included"
    return pd.DataFrame(rows).set_index("series"), monthly


def plot_smoke(summary):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
    stress = summary.loc[[f"slippage_{bps}bps" for bps in (0, 2, 5, 10)]]
    axes[0].plot(stress.slippage_bps, stress.net_usdt, marker="o")
    axes[0].set(xlabel="Extra adverse slippage per fill (bps)", ylabel="Net PnL (USDT)",
                title="Synthetic roundtrip: cost stress")
    funding = summary.loc[["funding_1_jitter0", "funding_-1_jitter0", "funding_0_jitter0"]]
    axes[1].bar(["Long", "Short", "Flat"], funding.funding_usdt,
                color=["#cb4b4b", "#269a85", "#8997a5"])
    axes[1].axhline(0, color="black", linewidth=0.6)
    axes[1].set(ylabel="Funding cashflow (USDT)", title="Synthetic positive funding rate")
    fig.suptitle("ACCOUNTING FIXTURES — no historical strategy performance", fontsize=11)
    return fig


def plot_development(daily):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    metrics, monthly = performance_tables(daily)
    nav = daily[NAV_COLUMNS]
    fig, axes = plt.subplots(3, 2, figsize=(14, 12), layout="constrained")
    (nav / nav.iloc[0]).plot(ax=axes[0, 0], title="Net equity / matched benchmarks (start=1)")
    (nav / nav.cummax() - 1).plot(ax=axes[0, 1], title="Drawdown")
    axes[0, 1].yaxis.set_major_formatter(PercentFormatter(1))
    monthly.plot.bar(ax=axes[1, 0], title="Monthly returns (edge months may be partial)")
    axes[1, 0].set_xticks(range(len(monthly)),
                         [x.strftime("%Y-%m") for x in monthly.index], rotation=60)
    axes[1, 0].yaxis.set_major_formatter(PercentFormatter(1))
    daily[["gross_exposure", "net_exposure"]].plot(ax=axes[1, 1], title="Exposure / NAV")
    daily[["commissions_usdt", "funding_cashflow_usdt"]].cumsum().plot(
        ax=axes[2, 0], title="Cumulative commissions (positive cost) / funding (signed)")
    turnover = daily.traded_notional_usdt.iloc[1:] / daily.strategy_nav.shift(1).iloc[1:]
    turnover.plot(ax=axes[2, 1], title="Daily traded notional / previous NAV (both sides)")
    fig.suptitle("2021–2022 DEVELOPMENT — marked NAV includes fees and funding")
    return fig, metrics, monthly
