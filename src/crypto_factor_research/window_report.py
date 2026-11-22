"""Re-renderable English tables, plots and notebook; not financial run identity."""

import csv
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DAY, HOUR, load_json, sha
from .repair import write_json
from .window_data import ms, window_label


def spot_benchmark(root, config, symbol, start, last):
    observed, bindings = {}, {}
    for month in pd.period_range(
        config["start"][:7], pd.Timestamp(config["stop_exclusive"]) - pd.Timedelta(days=1), freq="M"
    ).astype(str):
        folder = root / config["spot_root"] / symbol / month
        body = (folder / "archive.zip").read_bytes()
        meta = load_json(folder / "source.json")
        if (
            sha(folder / "archive.zip") != meta["sha256"]
            or meta["sha256"] != (folder / "checksum.txt").read_text().split()[0]
        ):
            raise ValueError("Spot source checksum mismatch")
        bindings[str(folder / "archive.zip")] = meta["sha256"]
        bindings[str(folder / "checksum.txt")] = sha(folder / "checksum.txt")
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            entries = archive.infolist()
            if len(entries) != 1 or entries[0].filename != f"{symbol}-1h-{month}.csv":
                raise ValueError("Spot archive identity mismatch")
            rows = csv.reader(io.StringIO(archive.read(entries[0]).decode("utf-8-sig")))
            for row in rows:
                if not row or not row[0].isdigit():
                    continue
                t = int(row[0])
                t = t // 1000 if t >= 100000000000000 else t
                if t in observed or t % HOUR:
                    raise ValueError("Spot duplicate/off-grid timestamp")
                observed[t] = (float(row[4]), float(row[5]), float(row[7]))
    if len(observed) != (ms(config["stop_exclusive"]) - start) // HOUR:
        raise ValueError("Spot calendar incomplete")
    entry, final = start + HOUR, last - HOUR
    a, b = observed[entry], observed[final - HOUR]
    if a[1] <= 0 or b[1] <= 0:
        raise ValueError("Spot execution volume unavailable")
    buy, sell = a[2] / a[1] * 1.0005, b[2] / b[1] * 0.9995
    units = 100000 / (buy * 1.001)
    final_cash = units * sell * 0.999
    rows = [
        {
            "timestamp": pd.Timestamp(t, unit="ms", tz="UTC").strftime("%Y-%m-%dT00:00:00Z"),
            "nav": 100000.0
            if t == start
            else final_cash
            if t > final
            else units * observed[t - HOUR][0],
        }
        for t in range(start, last + 1, DAY)
    ]
    return pd.DataFrame(rows), bindings


def report(root, config, path):
    import matplotlib

    from momentum_data.reporting.analysis import performance_tables

    from .first_window import checked

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root, path = Path(root), Path(path)
    summary = load_json(path / "simulation_summary.json")
    if not summary["success"]:
        raise ValueError("Some registered financial cases failed; no successful report")
    start, last = ms(config["start"]), ms(config["stop_exclusive"]) - DAY
    bench, source_bindings = {}, {}
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        frame, bindings = spot_benchmark(root, config, symbol, start, last)
        bench[symbol] = frame
        source_bindings.update(bindings)
    from .window_audit import attribution, audit_all

    audit = audit_all(config, path)
    asset, side = attribution(path)
    out = path / "report"
    out.mkdir(exist_ok=True)
    asset.to_csv(out / "asset_attribution.csv")
    side.to_csv(out / "side_attribution.csv")
    all_metrics, monthlies = [], {}
    for case in summary["cases"]:
        name = f"{case['case']}_{case['bps']}bps"
        folder = path / "results" / name
        checked(folder, "case_manifest.json")
        daily = pd.read_csv(folder / "engine_daily.csv")
        for symbol, col in [("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")]:
            if not daily.timestamp.equals(bench[symbol].timestamp):
                raise ValueError("Strategy/benchmark calendar mismatch")
            daily[col] = bench[symbol].nav
        daily.index = pd.to_datetime(daily.timestamp, utc=True)
        if not np.isfinite(daily[["strategy_nav", "btc_nav", "eth_nav"]]).all().all():
            raise ValueError("Nonfinite daily NAV")
        metric, monthly = performance_tables(daily)
        metric = metric.reset_index()
        metric["case"] = name
        all_metrics.append(metric)
        monthlies[name] = monthly
        if name == "lightgbm_5bps":
            daily.to_csv(out / "primary_daily.csv", index=False)
            primary = daily
    metrics = pd.concat(all_metrics, ignore_index=True)
    metrics.to_csv(out / "all_case_metrics.csv", index=False)
    monthly = monthlies["lightgbm_5bps"]
    monthly.to_csv(out / "monthly_returns.csv")
    primary_metrics = metrics[(metrics["case"] == "lightgbm_5bps")]
    primary_metrics.to_csv(out / "primary_metrics.csv", index=False)
    groups = metrics[
        (metrics["case"].str.startswith("random_")) & metrics.series.eq("strategy_nav")
    ]
    groups.to_csv(out / "random_control_distribution.csv", index=False)
    random_stats = (
        groups[["total_return", "Sharpe_rf0", "MDD"]].agg(["min", "median", "max"]).to_dict()
    )
    other = float((1 + monthly.strategy_nav.drop(monthly.strategy_nav.idxmax())).prod() - 1)
    strategy_metric = primary_metrics[primary_metrics.series.eq("strategy_nav")].iloc[0]
    random_comparison = {
        "registered_seeds": len(groups),
        "random_returns_strictly_above_model": int(
            groups.total_return.gt(strategy_metric.total_return).sum()
        ),
        "random_sharpes_strictly_above_model": int(
            groups.Sharpe_rf0.gt(strategy_metric.Sharpe_rf0).sum()
        ),
    }
    costs = {
        "total_commissions_usdt": float(primary.commissions_usdt.sum()),
        "net_funding_cashflow_usdt": float(primary.funding_cashflow_usdt.sum()),
        "traded_notional_usdt": float(primary.traded_notional_usdt.sum()),
        "one_way_turnover_over_mean_daily_nav": float(
            primary.traded_notional_usdt.sum() / primary.strategy_nav.mean()
        ),
    }
    write_json(
        out / "cost_and_random_comparison.json",
        {
            "random": random_comparison,
            "costs": costs,
            "positive_months": int(monthly.strategy_nav.gt(0).sum()),
        },
    )
    fig, ax = plt.subplots(figsize=(10, 4))
    for col, label in [
        ("strategy_nav", "Dynamic ML"),
        ("btc_nav", "BTC spot"),
        ("eth_nav", "ETH spot"),
    ]:
        ax.plot(primary.index, primary[col] / 100000, label=label)
    ax.set(title=config["start"][:4] + " retrospective replay", ylabel="NAV / initial capital")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out / "equity.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 2.8))
    values = monthly.strategy_nav.to_numpy() * 100
    ax.imshow(
        values.reshape(1, -1),
        cmap="RdYlGn",
        aspect="auto",
        vmin=-max(abs(values)),
        vmax=max(abs(values)),
    )
    ax.set_xticks(range(len(values)), [x.strftime("%b") for x in monthly.index])
    ax.set_yticks([0], [config["start"][:4]])
    for i, value in enumerate(values):
        ax.text(i, 0, f"{value:.1f}%", ha="center", va="center", fontsize=9)
    ax.set_title("Net monthly strategy returns (partial boundary months)")
    fig.tight_layout()
    fig.savefig(out / "monthly_returns.png", dpi=150)
    plt.close(fig)
    columns = ["case", "series", "total_return", "Sharpe_rf0", "MDD", "CAGR", "Calmar"]
    md = (
        "# Dynamic-universe annual results\n\n"
        + window_label(config)
        + ". Retrospective research; not fresh OOS.\n\n"
        + markdown_table(primary_metrics[columns])
        + "\n\nAll registered cases and random controls are retained in CSV.\n\nReturn excluding the best month: "
        + f"{other:.2%}"
        + ".\n\nExecution uses VWAP/mark proxies,fractional research lots and a current-cost fee assumption. It is not tick-level liquidation or historical fee reconstruction.\n"
    )
    md += (
        "\nRandom controls beating the model return: "
        + str(random_comparison["random_returns_strictly_above_model"])
        + " / "
        + str(random_comparison["registered_seeds"])
        + ". This is a limited descriptive benchmark, not proof of alpha.\n"
    )
    md += (
        "\n"
        + markdown_table(side.reset_index().rename(columns={"index": "side"}))
        + "\n\nSide values are cash contributions, not standalone portfolio returns.\n"
    )
    md += (
        "\n"
        + markdown_table(asset.reset_index().head(10))
        + "\n\nAsset contributions reconcile to account PnL; removing an asset would require a separate counterfactual replay.\n"
    )
    (out / "results.md").write_text(md)
    result = {
        "success": True,
        "independent_audit": audit,
        "window": window_label(config),
        "fresh_OOS": False,
        "registered_cases_completed": summary["completed_cases"],
        "primary_replay_identical": summary["primary_replay_identical"],
        "primary_metrics": primary_metrics.replace({np.nan: None}).to_dict("records"),
        "random_control_summary": random_stats,
        "random_comparison": random_comparison,
        "costs": costs,
        "return_excluding_best_month": other,
        "report_code_sha256": sha(Path(__file__)),
        "source_bindings": source_bindings,
        "output_hashes": {file.name: sha(file) for file in out.iterdir() if file.is_file()},
    }
    write_json(path / "report_summary.json", result)
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Dynamic-universe annual results\n"
                + window_label(config)
                + ". All cost/control cases are retained. This is not fresh OOS."
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from pathlib import Path\nimport pandas as pd\nfrom IPython.display import display, Image\nRUN_DIR = Path("
                + repr(str(path.resolve()))
                + ")\nREPORT = RUN_DIR / 'report'\ndisplay(pd.read_csv(REPORT / 'primary_metrics.csv'))\ndisplay(pd.read_csv(REPORT / 'all_case_metrics.csv'))"
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "display(Image(filename=str(REPORT / 'equity.png')))\ndisplay(Image(filename=str(REPORT / 'monthly_returns.png')))\ndisplay(pd.read_csv(RUN_DIR / 'model/shap_importance.csv'))"
            ],
        },
    ]
    write_json(
        path / "results.ipynb",
        {
            "cells": [dict(cell, id=f"first-window-{index}") for index, cell in enumerate(cells)],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        },
    )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"source_bindings", "output_hashes"}}
        ),
        flush=True,
    )
    return result


def markdown_table(frame):
    columns = list(frame.columns)
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in frame.itertuples(index=False, name=None):
        rows.append(
            "| "
            + " | ".join(
                f"{value:.6g}" if isinstance(value, float) else str(value) for value in row
            )
            + " |"
        )
    return "\n".join(rows)
