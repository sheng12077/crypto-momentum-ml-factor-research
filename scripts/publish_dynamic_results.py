"""Render public monthly results from aggregate JSON; no market data or backtest."""

import calendar
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pct(value):
    return f"{value:+.2%}"


def metric(year, case="lightgbm_5bps", series="strategy_nav"):
    return next(r for r in year["metrics"] if r["case"] == case and r["series"] == series)


def table(headers, rows):
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        + ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    )


def publish(root=ROOT):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    snapshot = json.loads((root / "docs/results/dynamic_annual_summary.json").read_text())
    years = snapshot["years"]
    for year in years:
        months = year["monthly_returns"]
        dates = [row["month"] for row in months]
        expected = [
            f"{year['year']}-{m:02}" for m in range(1, 11 if year["year"] == "2026" else 13)
        ]
        if dates != expected:
            raise ValueError("Unexpected monthly calendar: " + year["year"])
        for series in ["strategy_nav", "btc_nav", "eth_nav"]:
            values = [r[series] for r in months]
            if not all(math.isfinite(v) and v > -1 for v in values):
                raise ValueError("Invalid monthly returns")
            if (
                abs(
                    math.prod(1 + v for v in values)
                    - 1
                    - metric(year, series=series)["total_return"]
                )
                > 1e-8
            ):
                raise ValueError("Monthly/annual return mismatch")

    matrix = np.full((len(years), 12), np.nan)
    for i, year in enumerate(years):
        for row in year["monthly_returns"]:
            matrix[i, int(row["month"][-2:]) - 1] = row["strategy_nav"] * 100
    fig, ax = plt.subplots(figsize=(13, 4.5))
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("#e5e7eb")
    limit = float(np.nanmax(np.abs(matrix)))
    ax.imshow(np.ma.masked_invalid(matrix), cmap=cmap, vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(12), list(calendar.month_abbr)[1:])
    ax.set_yticks(
        range(len(years)), [y["year"] + (" (OOS)" if int(y["year"]) >= 2025 else "") for y in years]
    )
    ax.axhline(2.5, color="#334155", linewidth=1.5)
    for i in range(len(years)):
        for j in range(12):
            value = matrix[i, j]
            ax.text(
                j,
                i,
                f"{value:+.1f}%" if np.isfinite(value) else "—",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if np.isfinite(value) and abs(value) > limit * 0.75 else "black",
            )
    ax.set_title("LightGBM monthly net returns · dynamic universe · 5 bps slippage", pad=14)
    fig.text(
        0.5,
        0.02,
        "Separate annual accounts; UTC snapshot buckets; 2026 ends Oct 31 00:00 UTC. June 2026 uses assumed funding.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(root / "docs/assets/dynamic_monthly_returns.png", dpi=160)
    plt.close(fig)

    monthly_table = table(
        ["Year"] + list(calendar.month_abbr)[1:],
        [
            [y["year"]] + [pct(v / 100) if np.isfinite(v) else "—" for v in matrix[i]]
            for i, y in enumerate(years)
        ],
    )
    all_months = [(r["month"], r["strategy_nav"]) for y in years for r in y["monthly_returns"]]
    positive = sum(v > 0 for _, v in all_months)
    best, worst = max(all_months, key=lambda x: x[1]), min(all_months, key=lambda x: x[1])
    concentration_rows = []
    for y in years:
        rows = y["monthly_returns"]
        best_year = max(rows, key=lambda r: r["strategy_nav"])
        worst_year = min(rows, key=lambda r: r["strategy_nav"])
        excluded = (
            math.prod(1 + r["strategy_nav"] for r in rows if r["month"] != best_year["month"]) - 1
        )
        if abs(excluded - y["return_excluding_best_month"]) > 1e-8:
            raise ValueError("Best-month exclusion mismatch")
        concentration_rows.append(
            [
                y["year"],
                f"{sum(r['strategy_nav'] > 0 for r in rows)}/{len(rows)}",
                f"{best_year['month']} ({pct(best_year['strategy_nav'])})",
                f"{worst_year['month']} ({pct(worst_year['strategy_nav'])})",
                pct(excluded),
            ]
        )
    stats = (
        f"Positive months: **{positive}/{len(all_months)} ({positive / len(all_months):.1%})**; "
        f"median month: **{pct(statistics.median(v for _, v in all_months))}**. "
        f"Best: **{best[0]}, {pct(best[1])}**; worst: **{worst[0]}, {pct(worst[1])}**."
    )
    notes = (
        "Monthly returns compound daily NAV changes within UTC snapshot-date buckets. "
        "Each year starts a separate account; annual boundary liquidation and re-entry "
        "costs are included. October 2026 is partial; November/December are unavailable, "
        "not zero returns. These cells reconcile to the annual results, but do not form "
        "an uninterrupted capital simulation."
    )
    block = (
        "<!-- dynamic-monthly:start -->\n### Monthly net returns\n\n"
        "![LightGBM monthly net returns, 2022–2026](docs/assets/dynamic_monthly_returns.png)\n\n"
        + monthly_table
        + "\n\n"
        + stats
        + "\n\n"
        + notes
        + "\n\n"
        "2026 illustrates return concentration: excluding its best month, the remaining "
        "months compound to **−36.75%**, versus **−10.33%** for the reported year. "
        "This is a descriptive check, not a counterfactual trading strategy.\n\n"
        "[Detailed results: annual risk, monthly concentration, costs and controls](docs/DYNAMIC_RESULTS.md).\n"
        "<!-- dynamic-monthly:end -->"
    )
    readme_path = root / "README.md"
    readme = readme_path.read_text()
    start, end = "<!-- dynamic-monthly:start -->", "<!-- dynamic-monthly:end -->"
    if start in readme:
        a, b = readme.index(start), readme.index(end) + len(end)
        readme = readme[:a] + block + readme[b:]
    else:
        old = (
            "![2026 monthly net returns: LightGBM and equal factor scores](docs/assets/dynamic_2026_monthly_returns.png)\n\n"
            "*2026 only; boundary months are partial. The funding assumption below applies.*"
        )
        if old not in readme:
            raise ValueError("README monthly insertion point missing")
        readme = readme.replace(old, block)
    readme_path.write_text(readme)

    risk = table(
        [
            "Year",
            "Return",
            "Sharpe rf=0",
            "MDD",
            "Annual volatility",
            "Calmar",
            "BTC return / MDD",
            "ETH return / MDD",
        ],
        [
            [
                y["year"],
                pct(metric(y)["total_return"]),
                f"{metric(y)['Sharpe_rf0']:.2f}",
                pct(metric(y)["MDD"]),
                pct(metric(y)["annualized_volatility"]),
                f"{metric(y)['Calmar']:.2f}",
                " / ".join(pct(metric(y, series="btc_nav")[k]) for k in ["total_return", "MDD"]),
                " / ".join(pct(metric(y, series="eth_nav")[k]) for k in ["total_return", "MDD"]),
            ]
            for y in years
        ],
    )
    controls = table(
        [
            "Year",
            "Equal score return / MDD",
            "Momentum return / MDD",
            "Random returns above ML",
            "Random Sharpes above ML",
        ],
        [
            [
                y["year"],
                *[
                    " / ".join(pct(metric(y, case=c)[k]) for k in ["total_return", "MDD"])
                    for c in ["equal_groups_5bps", "momentum60_5bps"]
                ],
                f"{y['random_comparison']['random_returns_strictly_above_model']}/{y['random_comparison'].get('completed_seeds', y['random_comparison']['registered_seeds'])}",
                f"{y['random_comparison']['random_sharpes_strictly_above_model']}/{y['random_comparison'].get('completed_seeds', y['random_comparison']['registered_seeds'])}",
            ]
            for y in years
        ],
    )
    costs = table(
        ["Year", "Commissions, USDT", "Net funding, USDT", "Traded notional / mean daily NAV"],
        [
            [
                y["year"],
                f"{y['costs']['total_commissions_usdt']:,.2f}",
                f"{y['costs']['net_funding_cashflow_usdt']:+,.2f}",
                f"{y['costs']['one_way_turnover_over_mean_daily_nav']:.2f}×",
            ]
            for y in years
        ],
    )
    doc = (
        "# Dynamic-universe results\n\n"
        "LightGBM primary case: 5 bps adverse slippage, plus fees and funding. "
        "Each year starts with USDT 100,000 and an annual model fit on earlier years. "
        "2022–2023 are development, 2024 validation, and 2025–2026 designated OOS windows.\n\n"
        "## Annual performance and risk\n\n" + risk + "\n\n"
        "- **2022:** positive return during the crypto drawdown, with substantially smaller drawdown than both spot benchmarks.\n"
        "- **2023:** profitable with a 1.42 Sharpe, but lower return and Sharpe than BTC; long/short exposure did not capture the full bull-market gain.\n"
        "- **2024:** negative return despite rising BTC and ETH; ML portfolio selection did not translate into a profitable year.\n"
        "- **2025:** positive return while both spot benchmarks fell, but drawdown remained slightly larger than BTC.\n"
        "- **2026:** lost less than both spot benchmarks, yet drawdown exceeded BTC and returns depended heavily on the best month.\n\n"
        "These are observed outcomes, not causal attribution or proof of regime robustness. "
        "Dollar-neutral targets do not establish zero market beta. No aggregate Sharpe or "
        "drawdown is inferred by averaging annual metrics.\n\n"
        "## Monthly consistency and concentration\n\n"
        "![Monthly returns](assets/dynamic_monthly_returns.png)\n\n"
        + monthly_table
        + "\n\n"
        + stats
        + "\n\n"
        + notes
        + "\n\n"
        + table(
            ["Year", "Positive months", "Best month", "Worst month", "Return excluding best month"],
            concentration_rows,
        )
        + "\n\n"
        "Excluding the best month compounds the remaining observed monthly returns. "
        "It does not rerun the portfolio without that month's trades and is not evidence "
        "of what a modified strategy would have earned.\n\n"
        "## Matched controls\n\n" + controls + "\n\n"
        "Random counts are descriptive, not p-values: only 20 seeds were registered, "
        "and selection decisions were informed by development results. In 2026 only 19 "
        "controls completed; random_1012 had nonpositive marked NAV and remains failed. "
        "The denominator above is 19 for that year; the full 20-control comparison is "
        "unavailable. No terminal return is assigned to the failed control.\n\n"
        "The equal-score and momentum controls have severe annual swings and drawdowns; "
        "their strongest years alone do not establish a reliable strategy. Positive "
        "Sharpe can coexist with a negative compound return under extreme volatility "
        "because Sharpe uses arithmetic daily returns.\n\n"
        "## Costs and turnover\n\n" + costs + "\n\n"
        "Funding is positive for a net receipt and negative for a net payment. "
        "Commissions and funding are included in NAV. Slippage is embedded in fills, "
        "not included in the commission column; the README separately shows 10/20 bps "
        "stress results. The turnover statistic is total absolute traded notional divided "
        "by mean daily NAV; it is not halved or annualized for partial 2026.\n\n"
        "## Scope and reproducibility\n\n"
        "2026 June 24 missing funding events use the adjacent original-rate mean. "
        "The later anchor is future information for accounting; this is not proven "
        "settlement or a deployable real-time assumption. The primary case used 12 "
        "estimated payments totaling −17.67 USDT. All 29 completed 2026 cases passed "
        "independent accounting checks; the full 30-case suite remains unsuccessful.\n\n"
        "VWAP/mark proxy fills, fractional research lots, current fee assumptions and "
        "absence of an exchange liquidation engine limit real-money interpretation. "
        "The results support a reproducible research project, not a stable-profit or "
        "deployment-readiness claim. Earlier years use their saved engine revision; "
        "2025–2026 use the exact filled-quantity adapter, recorded in run provenance.\n\n"
        "Aggregate values and original report/monthly-source hashes are in "
        "[the public snapshot](results/dynamic_annual_summary.json). Rebuild this "
        "document and the figure without private data using "
        "`python scripts/publish_dynamic_results.py`. No model fit or simulation occurs.\n"
    )
    (root / "docs/DYNAMIC_RESULTS.md").write_text(doc)
    print(
        json.dumps(
            {
                "success": True,
                "years": len(years),
                "months": len(all_months),
                "positive_months": positive,
                "backtest_executed": False,
            }
        )
    )


if __name__ == "__main__":
    publish()
