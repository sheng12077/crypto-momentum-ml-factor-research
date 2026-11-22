"""Publish verified saved results to README, English notes and a monthly heatmap.

No model fit, download or historical simulation. Regenerate after a verified CLI run.
"""

import contextlib
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

from ..backtest import workflow as source
from ..integrity import sha, checked_manifest, frozen_path
from ..settings import DATA_ROOT

ROOT = source.ROOT
ASSETS = ROOT / "docs/assets"
DETAILS = ROOT / "docs/CONTINUOUS_RECONSTRUCTION_RESULTS.md"
IMAGE = ASSETS / "continuous_monthly_returns.png"
LABELS = {
    "strategy_nav": "Strategy (5 bps slippage)",
    "btc_nav": "BTC spot buy-and-hold",
    "eth_nav": "ETH spot buy-and-hold",
}


def pct(x):
    return f"{x:+.2%}"


def table(headers, rows):
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        + ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    )


def verify_inputs():
    # Verifies immutable code/input contracts, replay/case files and every saved report artifact.
    with contextlib.redirect_stdout(io.StringIO()):
        source.print_summary()
    summary = json.loads((source.BASE / "summary.json").read_text())
    if not summary["success"] or not summary["report_verified"] or summary["fresh_OOS"]:
        raise ValueError("Expected completed retrospective reconstruction")
    daily = source.validate_daily(pd.read_csv(source.TABLES / "daily_5bps.csv"))
    metrics, monthly = source.performance_tables(daily)
    saved = pd.read_csv(source.TABLES / "monthly_returns_5bps.csv", index_col=0, parse_dates=True)
    pd.testing.assert_frame_equal(
        monthly, saved, check_exact=False, atol=1e-12, rtol=0, check_freq=False
    )
    yearly = pd.read_csv(source.TABLES / "year_slices_5bps.csv")
    expected = source.year_slices(daily)
    pd.testing.assert_frame_equal(
        yearly, expected, check_exact=False, atol=1e-12, rtol=0, check_dtype=False
    )
    if len(monthly) != 58 or len(daily) != 1765:
        raise ValueError("Unexpected reporting scope")
    for name in LABELS:
        reported = next(r for r in summary["primary_results"] if r["series"] == name)
        if abs(metrics.loc[name, "total_return"] - reported["total_return"]) > 1e-12:
            raise ValueError("Summary differs from saved NAV")
        compounded = np.prod(1 + yearly.loc[yearly.series == name, "total_return"]) - 1
        if abs(compounded - metrics.loc[name, "total_return"]) > 1e-12:
            raise ValueError("Annual slices omit a cross-year return")
    return summary, daily, metrics, monthly, yearly


def heatmap(monthly, yearly):
    s = monthly.strategy_nav
    grid = np.full((5, 12), np.nan)
    for stamp, value in s.items():
        grid[stamp.year - 2022, stamp.month - 1] = value
    cmap = LinearSegmentedColormap.from_list("loss_neutral_gain", ["#bb493d", "#f7f8fa", "#16766d"])
    cmap.set_bad("#e4e8ed")
    with plt.rc_context(
        {"font.family": "DejaVu Sans", "font.size": 11, "savefig.facecolor": "white"}
    ):
        fig = plt.figure(figsize=(15.8, 6.2), facecolor="white")
        axes = fig.add_gridspec(
            1,
            2,
            width_ratios=[12, 1.55],
            left=0.16,
            right=0.975,
            top=0.76,
            bottom=0.24,
            wspace=0.035,
        )
        ax, totals = fig.add_subplot(axes[0]), fig.add_subplot(axes[1])
        image = ax.imshow(
            np.ma.masked_invalid(grid),
            cmap=cmap,
            norm=TwoSlopeNorm(vmin=-0.25, vcenter=0, vmax=0.25),
            aspect="auto",
        )
        ax.set_xticks(
            range(12),
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        )
        ax.axhline(2.5, color="#344050", linewidth=2.2)
        ax.xaxis.tick_top()
        ax.tick_params(axis="both", length=0, pad=9)
        ax.set_yticks(
            range(5),
            [
                "2022  |  Development",
                "2023  |  Development",
                "2024  |  Validation",
                "2025  |  OOS dates, full path",
                "2026* |  OOS dates, full path",
            ],
        )
        for i in range(5):
            for j in range(12):
                v = grid[i, j]
                text = "--" if np.isnan(v) else f"{v:+.2%}"
                ax.text(
                    j,
                    i,
                    text,
                    ha="center",
                    va="center",
                    fontsize=10.4,
                    color="white" if np.isfinite(v) and abs(v) >= 0.16 else "#14202b",
                )
        ax.set_xticks(np.arange(-0.5, 12, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.tick_params(which="minor", bottom=False, left=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        totals.set_facecolor("#edf1f5")
        totals.set(xlim=(-0.5, 0.5), ylim=(4.5, -0.5), xticks=[0], yticks=[])
        totals.set_xticklabels(["Period return"])
        totals.xaxis.tick_top()
        totals.tick_params(length=0, pad=9)
        annual = yearly[yearly.series == "strategy_nav"].set_index("year").total_return
        for i, y in enumerate(range(2022, 2027)):
            totals.text(
                0, i, pct(annual[y]), ha="center", va="center", fontweight="bold", color="#14202b"
            )
        for spine in totals.spines.values():
            spine.set_visible(False)
        fig.text(
            0.16, 0.94, "Monthly net returns (%)", fontsize=23, fontweight="bold", color="#14202b"
        )
        fig.text(
            0.16,
            0.875,
            "One continuous account | 5 bps taker fee + 5 bps adverse slippage per fill | funding included",
            fontsize=11,
            color="#435164",
        )
        fig.text(
            0.16,
            0.82,
            "Full-path monthly returns; 2025-26 rows carry prior holdings and are not the separate OOS account",
            fontsize=11,
            color="#8f4035",
        )
        bar = fig.add_axes([0.16, 0.145, 0.30, 0.025])
        colorbar = fig.colorbar(image, cax=bar, orientation="horizontal")
        colorbar.set_ticks([-0.25, 0, 0.25])
        colorbar.ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        colorbar.outline.set_visible(False)
        fig.text(
            0.49,
            0.15,
            "Color scale applies to monthly returns only; period returns compound, not sum.",
            fontsize=9,
            color="#435164",
        )
        fig.text(
            0.16,
            0.075,
            "Monthly returns compound daily NAV changes grouped by UTC snapshot date. Labels follow the saved report convention.",
            fontsize=9,
            color="#435164",
        )
        fig.text(
            0.16,
            0.035,
            "*2026 ends Oct 31 at 00:00 UTC (partial October); Nov-Dec are unobserved, not zero. All returns are simulated.",
            fontsize=9,
            color="#435164",
        )
        ASSETS.mkdir(parents=True, exist_ok=True)
        fig.savefig(IMAGE, dpi=160)
        plt.close(fig)


def original_oos():
    """Read the registered separate OOS account, not a slice of the later full path."""
    from importlib.metadata import version

    base = DATA_ROOT / "interim/final_holdout/v20261122_003"
    code = json.loads((base / "code_contract.json").read_text())
    for name, digest in code["code_hashes"].items():
        if sha(frozen_path(name)) != digest:
            raise ValueError("Original OOS source changed: " + name)
    if (
        sha(frozen_path("experiments/015_final_holdout_2025_2026.md"))
        != code["registration_sha256"]
    ):
        raise ValueError("OOS preregistration changed")
    for name, expected in code["runtime"].items():
        if version(name) != expected:
            raise ValueError("OOS runtime mismatch: " + name)
    run = json.loads((base / "results/run_contract.json").read_text())
    if (
        run["code_contract_sha256"] != sha(base / "code_contract.json")
        or run["prepared_sha256"] != sha(base / "prepared/manifest.json")
        or run["spot_sha256"] != sha(base / "spot_benchmarks/summary.json")
    ):
        raise ValueError("Original OOS run contract mismatch")
    results = {}
    for bps in (5, 10):
        folder = base / f"results/continuous/lightgbm/slippage_{bps}bps"
        meta = checked_manifest(folder, "_complete.json")
        if meta["run_contract_sha256"] != sha(base / "results/run_contract.json"):
            raise ValueError("OOS case belongs to another run")
        daily = source.validate_daily(pd.read_csv(folder / "daily.csv"))
        if daily.index[0] != pd.Timestamp("2025-01-01", tz="UTC") or daily.index[
            -1
        ] != pd.Timestamp("2026-10-31", tz="UTC"):
            raise ValueError("Original OOS calendar mismatch")
        if daily.strategy_nav.iloc[0] != 100000.0 or daily.gross_exposure.iloc[0] != 0:
            raise ValueError("Original OOS must begin with fresh cash, not inherited holdings")
        metrics, monthly = source.performance_tables(daily)
        saved = pd.read_csv(folder / "metrics.csv", index_col=0)
        pd.testing.assert_frame_equal(
            metrics, saved, check_exact=False, atol=1e-12, rtol=0, check_dtype=False
        )
        results[bps] = (daily, metrics, monthly)
    return base, results


def period_disclosure(daily, full_metrics):
    base, oos = original_oos()
    original, metrics, monthly = oos[5]
    carry = daily.loc[original.index[0] : original.index[-1]]
    if not carry.index.equals(original.index):
        raise ValueError("Full-path/OOS comparison dates differ")
    carry_metrics, _ = source.performance_tables(carry)
    phases = table(
        ["Period", "Role", "Interpretation"],
        [
            [
                "2022--2023",
                "Development / selection",
                "Used to inform strategy and execution choices",
            ],
            ["2024", "Frozen validation", "Revealed before the final holdout"],
            [
                "2025--October 2026",
                "Original final OOS; now disclosed",
                "Protocol015 separate account; frozen annual expanding fits",
            ],
            [
                "2022--October 2026",
                "Full retrospective reconstruction",
                "Protocol016 registered after all annual results were observed",
            ],
        ],
    )
    rows = []
    for label, m in [
        ("Full path (2022--2026)", full_metrics.loc["strategy_nav"]),
        ("Original OOS account (2025--2026)", metrics.loc["strategy_nav"]),
        ("OOS-date slice of full path; carry-in diagnostic", carry_metrics.loc["strategy_nav"]),
    ]:
        rows.append([label, pct(m.total_return), pct(m.CAGR), f"{m.Sharpe_rf0:.3f}", pct(m.MDD)])
    overview = table(["Account / period", "Return", "CAGR", "Sharpe (rf=0)", "MDD"], rows)
    controls = table(
        ["Original OOS series", "Return", "CAGR", "Sharpe (rf=0)", "MDD"],
        [
            [
                LABELS[name],
                pct(row.total_return),
                pct(row.CAGR),
                f"{row.Sharpe_rf0:.3f}",
                pct(row.MDD),
            ]
            for name, row in metrics.iterrows()
        ],
    )
    stress = oos[10][1].loc["strategy_nav"]
    strategy_months = monthly.strategy_nav
    full_section = f"""## Full period versus original OOS

{phases}

{overview}

All primary rows include 5 bps adverse slippage plus 5 bps perpetual taker fees and
Funding. The original OOS account starts with USDT 100,000 in cash on Jan 1, 2025;
it does not inherit 2024 positions. The full-path diagnostic carries positions/capital
from 2024 and is rebased at exactly the same Jan 1, 2025 NAV timestamp. It is **not**
a substitute OOS result. The +84.06% whole-period result is also **not all OOS**.
All comparisons end Oct 31, 2026 00:00 UTC; the last civil day is not included.
Development years may contain chronological forward forecasts but were used for
rule selection; that does not make them the clean final test.

![Full path and original OOS equity](assets/full_period_vs_oos.png)

### Original OOS benchmark comparison

{controls}

Original OOS 10 bps strategy stress: return **{pct(stress.total_return)}**,
Sharpe **{stress.Sharpe_rf0:.3f}**, MDD **{pct(stress.MDD)}**. Primary OOS:
**{int((strategy_months > 0).sum())}/{len(strategy_months)} positive months**.
Models use frozen annual expanding windows: 2025 uses matured 2021--2024 labels;
2026 may use matured 2025 labels, as preregistered. This is walk-forward evaluation,
not a single model trained once and held unchanged throughout OOS.

The OOS was originally withheld and is now revealed. Reusing these dates for new
choices does not create a new independent OOS. The 37-identifier conditional-universe,
execution/funding proxy and incomplete matched momentum-control limitations still
apply. The ML OOS cases are verified; the broader protocol's blocked EOS control
cases are not converted into completed cases by this publication.

The heatmap below belongs to the **full retrospective account**, including its
2025--2026 carry-in holdings. It must not be read as the original OOS account's monthly
return table. The latter's exact monthly values are reported separately below.
"""
    monthly_rows = []
    for y in (2025, 2026):
        g = {t.month: v for t, v in strategy_months.items() if t.year == y}
        monthly_rows.append([str(y)] + [pct(g[m]) if m in g else "N/A" for m in range(1, 13)])
    oos_month_table = table(
        [
            "Original OOS account",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        monthly_rows,
    )
    full_section += (
        "\n### Original OOS monthly net returns\n\n"
        + oos_month_table
        + "\n\nMonthly values use the same ending-UTC-NAV-date buckets as the existing reports.\n"
    )
    # Visually isolate full-path development/validation from the separate original OOS account.
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), layout="constrained")
    colors = {"strategy_nav": "#16766d", "btc_nav": "#cd8a2c", "eth_nav": "#5b70a5"}
    for ax, frame, title in [
        (axes[0], daily, "Full path | retrospective | 2022--2026"),
        (axes[1], original, "Original final OOS | disclosed | 2025--2026"),
    ]:
        for name, label in LABELS.items():
            ax.plot(
                frame.index,
                frame[name] / frame[name].iloc[0],
                label=label,
                color=colors[name],
                linewidth=1.5,
            )
        ax.set(title=title, ylabel="Equity / initial account NAV", xlabel="UTC NAV snapshot")
        ax.axhline(1, color="#7a8593", lw=0.6)
        ax.grid(alpha=0.18)
        ax.legend(fontsize=8)
    for a, b, color in [
        ("2022-01-01", "2024-01-01", "#f1dccf"),
        ("2024-01-01", "2025-01-01", "#dae4f1"),
        ("2025-01-01", "2026-10-31", "#daeee8"),
    ]:
        axes[0].axvspan(
            pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC"), color=color, alpha=0.35
        )
    axes[0].axvline(pd.Timestamp("2025-01-01", tz="UTC"), color="#344050", ls="--", lw=1)
    fig.suptitle("Separate account definitions: full-path gains are not all OOS", fontsize=13)
    fig.savefig(ASSETS / "full_period_vs_oos.png", dpi=150)
    plt.close(fig)
    readme_section = full_section.replace(
        "assets/full_period_vs_oos.png", "docs/assets/full_period_vs_oos.png"
    )
    # Keep README compact while the detailed page retains benchmark/monthly explanations.
    readme_section = readme_section.split("### Original OOS benchmark comparison")[0]
    readme_section += "\nOriginal OOS benchmarks and monthly results: [detailed period disclosure](docs/CONTINUOUS_RECONSTRUCTION_RESULTS.md#full-period-versus-original-oos).\n"
    provenance = f"\nOriginal OOS source: `{base.relative_to(ROOT)}`; case 5 bps manifest SHA256: `{sha(base / 'results/continuous/lightgbm/slippage_5bps/_complete.json')}`.\n"
    return readme_section, full_section + provenance


def publish():
    summary, daily, metrics, monthly, yearly = verify_inputs()
    heatmap(monthly, yearly)
    period_readme, period_details = period_disclosure(daily, metrics)
    returns = monthly.strategy_nav
    positive = int((returns > 0).sum())
    annual = yearly.pivot(index="year", columns="series", values="total_return")
    annual_rows = [
        [str(y) + (" (partial)" if y == 2026 else ""), *[pct(annual.loc[y, n]) for n in LABELS]]
        for y in annual.index
    ]
    annual_table = table(["Year", "Strategy", "BTC spot", "ETH spot"], annual_rows)
    whole_rows = []
    for name, label in LABELS.items():
        m = metrics.loc[name]
        whole_rows.append(
            [
                label,
                pct(m.total_return),
                pct(m.CAGR),
                f"{m.Sharpe_rf0:.3f}",
                pct(m.MDD),
                pct(m.annualized_volatility),
                f"{m.Calmar:.3f}",
            ]
        )
    stress = summary["stress_strategy_results"]
    whole_rows.insert(
        1,
        [
            "Strategy (10 bps slippage)",
            pct(stress["total_return"]),
            pct(stress["CAGR"]),
            f"{stress['Sharpe_rf0']:.3f}",
            pct(stress["MDD"]),
            pct(stress["annualized_volatility"]),
            f"{stress['Calmar']:.3f}",
        ],
    )
    whole_table = table(
        ["Series", "Total return", "CAGR", "Sharpe (rf=0)", "MDD", "Annual vol.", "Calmar"],
        whole_rows,
    )
    since2024, _ = source.performance_tables(daily.loc["2023-12-31":])
    recent_table = table(
        ["Series", "2024 onward return", "Sharpe (rf=0)", "MDD"],
        [
            [LABELS[n], pct(row.total_return), f"{row.Sharpe_rf0:.3f}", pct(row.MDD)]
            for n, row in since2024.iterrows()
        ],
    )
    win_rows = []
    for y, group in returns.groupby(returns.index.year):
        win_rows.append(
            [
                str(y),
                f"{int((group > 0).sum())}/{len(group)}",
                pct(group.median()),
                pct(group.max()),
                pct(group.min()),
            ]
        )
    win_table = table(
        ["Year", "Positive months", "Median month", "Best month", "Worst month"], win_rows
    )
    month_rows = []
    for y in range(2022, 2027):
        group = {t.month: v for t, v in returns.items() if t.year == y}
        month_rows.append(
            [str(y)]
            + [pct(group[m]) if m in group else "N/A" for m in range(1, 13)]
            + [pct(annual.loc[y, "strategy_nav"])]
        )
    month_table = table(
        [
            "Year",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
            "Period",
        ],
        month_rows,
    )
    gates = table(
        ["Registered descriptive gate", "Result"],
        [[k, "Pass" if v else "Fail"] for k, v in summary["evidence_gates"].items()],
    )
    bridge = []
    for y in range(2023, 2027):
        a = pd.Timestamp(f"{y - 1}-12-31", tz="UTC")
        b = pd.Timestamp(f"{y}-01-01", tz="UTC")
        bridge.append(
            [str(y), pct(daily.loc[b, "strategy_nav"] / daily.loc[a, "strategy_nav"] - 1)]
        )
    inputs = [
        source.BASE / "contract.json",
        source.BASE / "summary.json",
        source.BASE / "report_complete.json",
        source.TABLES / "daily_5bps.csv",
        source.TABLES / "monthly_returns_5bps.csv",
        source.TABLES / "year_slices_5bps.csv",
    ]
    hashes = "\n".join(f"- `{p.relative_to(ROOT)}`: `{sha(p)}`" for p in inputs)
    details = f"""# Continuous reconstruction results: 2022--October 2026

This is an uninterrupted NautilusTrader simulation using frozen annual model caches,
not a product of independent annual NAV resets. All years were already inspected
when Experiment 016 was registered. The full path is retrospective, not fresh OOS.

{period_details}

## Whole-path results

Start: 2022-01-01 00:00 UTC. Last NAV: 2026-10-31 00:00 UTC; final liquidation
2026-10-30 23:00 UTC. 1,765 NAV snapshots / 1,764 daily returns. Initial cash
USDT 100,000; primary ending NAV USDT {summary["ending_nav"]:,.2f}.

{whole_table}

Perpetual fees are 5 bps taker per fill, no BNB discount, plus the indicated adverse
slippage. Funding is included using completed-hour mark proxies and pre-fill holdings.
Spot benchmarks hold fixed units from Jan 1 2022 02:00 UTC to the final sale, with
10 bps taker fee and 5 bps slippage each side. Different exposures prevent interpreting
this simple comparison as a market-beta-adjusted alpha estimate. Historical rates
are simulation assumptions; the project does not certify every historical fee tier.

## Monthly returns

![Strategy monthly net returns](assets/continuous_monthly_returns.png)

{month_table}

Cells compound daily marked-equity returns, net of fees/funding/slippage, grouped
by the ending UTC NAV snapshot date. These are the existing report's month buckets,
not a newly reconstructed exchange-calendar month-end series. For example, a
return ending Feb 1 00:00 UTC belongs to February, although its interval starts Jan 31.
January 2022 starts with initial NAV; October 2026 ends at Oct 31 00:00 UTC and omits
that civil day's trading. Missing November/December cells are N/A, never zero.
Period totals compound the monthly cells; they are not sums or annualized partial years.

{win_table}

There are **{positive}/{len(returns)} positive months ({positive / len(returns):.2%})**; the
monthly median is **{pct(returns.median())}**. Best: **{returns.idxmax():%Y-%m},
{pct(returns.max())}**. Worst: **{returns.idxmin():%Y-%m}, {pct(returns.min())}**.
The best month accounts for {summary["best_month_cash_profit_share"]:.2%} of additive
net cash profit along this path. Compounding the other months gives
{pct(summary["other_months_compounded_return"])}; this is a descriptive concentration
check, not an executable counterfactual strategy or proof of stable performance.

## Continuous annual slices

{annual_table}

These slices include the return ending Jan 1 in its new year, using the preceding
Dec 31 NAV as the base. 2022 starts at the initial NAV. Their products reconcile
to the whole-period return; there are no synthetic flat bridges or annual liquidations.
The two-week phase still restarts at the first Monday of each year as originally
specified, which can create 7/21-day year-crossing intervals. New annual scores
apply at the next scheduled rebalance; the account keeps existing quantities until then.

The return ending Jan 1 alone is:

{table(["Year", "Cross-year daily strategy return"], bridge)}

Standalone annual backtests start from fresh cash and close at their own endpoint;
carry-over holdings, accumulated capital and omitted bridge days explain why those
results need not match these slices. The 2025 continuous slice is +40.58%, not the
previous +30.61% standalone run; do not mix the two definitions.

## How much comes after development?

2022--2023 informed strategy/execution selection. 2024 was a frozen validation;
2025--2026 were originally held out and are now disclosed. The uninterrupted
reconstruction was authorized after all of those results were observed. Existing
separate holdout reports retain their own protocol and account boundaries.

The following diagnostic starts at Dec 31 2023 NAV and includes all returns ending
in 2024 onward. It was calculated for reporting, not registered as a new independent test:

{recent_table}

The full-period +84.06% therefore should not be presented as evidence that returns
were uniformly strong. 2024 and partial 2026 lose money, and October 2026 alone
loses 20.33%. 2025 contributes strongly. The post-development aggregate is only
+8.09%; most of the full-period compounding advantage comes from development years.
A positive-month hit rate below 50% alone does not invalidate a strategy: payoff
sizes matter. The weak post-development risk-adjusted result and large loss month
are more consequential than the hit rate alone. A month-by-month heatmap reveals
this unevenness but cannot establish significance or deployment readiness on its own.

## Registered gates and accounting verification

{gates}

These are descriptive screening thresholds from Experiment 016, not significance
tests. Two financial cases and one exact primary replay completed; all required
source proxies passed preflight, annual cash resets=0, new model fits=0. The report
requires independent source-VWAP/slippage/fee and pre-fill funding reconstruction,
daily-ledger reconciliation and ending-ledger error <= USDT 0.01. Contracts and
saved case/report hashes were reverified before generating these documents.

Primary cumulative taker fees: USDT {summary["fees_usdt"]:,.2f}; signed funding
cashflow: USDT {summary["funding_usdt"]:,.2f}; gross traded notional (both sides):
USDT {summary["gross_traded_notional_usdt"]:,.2f}. Cumulative fees are cash amounts
along a changing-capital path, not a simple percentage drag on starting capital.
SHAP remains annual prediction attribution, not causal attribution of trading profit.

## Supported conclusion and unresolved limits

The retrospective path shows lower realized volatility/drawdown than unscaled
BTC/ETH holding and positive returns under the registered 10 bps slippage stress.
Monthly consistency is weak: fewer than half the months are profitable, the median
month is negative, and the recent period includes a large monthly loss. This supports
retaining the project as a reproducible research result and considering a separately
specified forward paper evaluation, not calling it a proven profitable live strategy.

The 37-identifier cohort is conditional and retrospectively reviewed; its historical
publication vintage is not proven. Hourly VWAP/slippage and completed-hour funding
marks approximate execution; historical lots, margin, liquidation, order-book impact
and live operational performance are not certified. No portfolio risk guarantee
follows from the lower historical MDD. The momentum-only control remains blocked
by missing verified EOS terminal settlement evidence and is not replaced or silently
excluded to claim alpha. No fresh OOS remains in these inspected dates.

## Reproduce and audit

From the WSL funding-strategy environment, run the existing simulator first if
results are absent; then publish the verified saved outputs:

```bash
python scripts/run_continuous_reconstruction.py --stage all
python scripts/run_continuous_reconstruction.py --stage summary
python scripts/publish_continuous_results.py
```

Publishing performs no fitting, downloading or historical simulation. It reproduces
monthly/annual summaries from saved daily NAV and checks the report hashes first.
See [runbook](CONTINUOUS_RECONSTRUCTION_RUNBOOK.md),
[registration](../experiments/016_continuous_2022_2026.md) and
[English notebook](../notebooks/continuous_reconstruction_results.ipynb).
Only summarized results and the figure are published in Git; source data stay ignored.

Historical contracts retain their original logical source names. Original script
bytes now live under `research/legacy/scripts/`, and original analysis source under
`research/legacy/src/`; the active verifier resolves these preserved files rather
than deleting or revising the old contracts. Refactored replays have a separate
package contract and must produce identical financial hashes.

Verified source hashes for this publication:

{hashes}

Publisher SHA256: `{sha(Path(__file__))}`.
"""
    DETAILS.write_text(details, encoding="utf-8")
    readme = ROOT / "README.md"
    previous = readme.read_text()
    if "## Research archive" in previous:
        archive = previous.split("## Research archive", 1)[1].strip()
    elif "## Current research notes" in previous:
        archive = previous.split("## Current research notes", 1)[1].strip()
    else:
        raise ValueError("Preserve the existing README archive before publishing")
    import re

    def archive_link(match):
        target = match.group(1)
        if (
            "://" not in target
            and not (ROOT / target).exists()
            and (ROOT / "research/legacy" / target).exists()
        ):
            return "](" + "research/legacy/" + target + ")"
        return match.group(0)

    archive = re.sub(r"\]\(([^)]+)\)", archive_link, archive)
    readme.write_text(
        f"""# Crypto Cross-Sectional Factor Research

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![NautilusTrader engine](https://img.shields.io/badge/Engine-NautilusTrader-334155)](src/momentum_data/backtest/engine.py)
[![Checks verified locally](https://img.shields.io/badge/Checks-verified_locally-16876B)](docs/PACKAGE_MIGRATION_VERIFICATION.md)
[![Retrospective research](https://img.shields.io/badge/Research-retrospective-64748B)](docs/CONTINUOUS_RECONSTRUCTION_RESULTS.md)

A reproducible, medium-frequency crypto long/short research project using annual
LightGBM forecasts and NautilusTrader execution/accounting. Momentum, funding and
aggressive-buy/sell imbalance rank a conditional 37-asset USDT-perpetual cohort.

**Current status: completed retrospective backtest; no live profitability claim.**
The uninterrupted 2022--October 2026 account is net profitable with lower historical
volatility/drawdown than BTC/ETH holding, but monthly consistency is weak and results
are substantially stronger in development years. Paper/live trading is not implemented
or certified by these results.

{period_readme}

## Continuous performance (full retrospective account)

{whole_table}

The account starts with USDT 100,000 on Jan 1 2022. Last valuation is **Oct 31 2026
00:00 UTC**, not the end of that civil day. Positions and capital persist across years;
there is one final liquidation and no yearly cash reset. Spot benchmarks buy once,
hold fixed units and sell once. All periods are already inspected; this reconstruction
is **not a fresh OOS test**. See [full results and limitations](docs/CONTINUOUS_RECONSTRUCTION_RESULTS.md).

## Monthly net returns

![Continuous strategy monthly net returns](docs/assets/continuous_monthly_returns.png)

- Positive months: **{positive}/{len(returns)} ({positive / len(returns):.2%})**; median month **{pct(returns.median())}**.
- Best month: **{returns.idxmax():%Y-%m}, {pct(returns.max())}**; worst: **{returns.idxmin():%Y-%m}, {pct(returns.min())}**.
- Return excluding the best month: **{pct(summary["other_months_compounded_return"])}** (descriptive compounding check).
- From 2024 onward: **{pct(since2024.loc["strategy_nav", "total_return"])}**, versus **+84.06%** over the full path.

Monthly values compound daily NAV changes grouped by UTC snapshot date, using the
saved report's bucket convention. October 2026 is partial; November/December are
unobserved. Green months do not establish a persistent edge or statistical significance.

{annual_table}

2022--2023 informed development; 2024 was frozen validation; 2025--2026 were the
original holdout, now revealed. The continuous reconstruction was registered after
all results were observed. Annual slices include the cross-year daily return and
therefore differ from separately liquidated, fresh-cash annual runs.

## Frozen strategy and simulation

- Five inputs across three groups: 20/60/120-day momentum, seven-day funding,
  seven-day taker-quote imbalance. The momentum horizons are model features,
  not a staged-entry position-control rule. No Size feature or buffer in this version.
- Existing annual expanding-window model caches; strict matured-label cutoffs.
  LightGBM parameters and forecasts are unchanged; annual SHAP is verified.
- Top five long / bottom five short, equal +/-10% target NAV per asset; at least
  20 eligible candidates. Target gross exposure 100%, target net notional zero;
  actual exposures drift. This is not a guarantee of zero market beta.
- Two-week rebalance, first-Monday anchor per year; actual quantities held between
  decisions. Cross-year intervals can be 7/21 days. Signal cutoff 00:00 UTC,
  sizing at 01UTC, prior-hour VWAP execution proxy at 02UTC.
- Perpetual taker fee 5 bps, no BNB discount; adverse slippage 5/10 bps per fill.
  Funding uses observed rates and a completed-hour mark proxy on pre-fill holdings.
  BTC/ETH spot benchmarks use 10 bps taker + 5 bps slippage per side.
- Required held-price/terminal checks, source-price/fee/funding reconstruction,
  daily-ledger reconciliation and an exact primary financial replay. Historical
  lots/margin/liquidation and order-book impact are not certified.

The conditional cohort's historical publication vintage is unresolved. A matched
momentum-only control has an unverified EOS terminal settlement and cannot support
an alpha claim. Lower simulated MDD does not prove live safety or future returns.

## Project structure

```text
src/momentum_data/
    data/          # hourly stores, benchmarks and complete input checks
    features/      # past-only factor definitions and history validation
    models/        # frozen annual model/training/prediction/SHAP verification
    portfolio/     # ranking and two-week portfolio schedule
    backtest/      # Nautilus execution, Funding, independent ledger audit
    reporting/     # metrics, publication and monthly heatmap
    cli.py         # public commands
scripts/           # three thin compatibility/demo entry points
config/            # named frozen-run paths and execution assumptions
notebooks/         # current English results reader
research/legacy/   # preserved earlier research layout and frozen source bytes
experiments/       # original preregistrations
```

[Architecture and migration notes](docs/PROJECT_STRUCTURE.md) explain which paths
are active, how frozen contracts survive relocation, and how historical tools are
kept separate. The public package does not import legacy scripts. Archived model
training/acquisition pipelines remain research evidence; the current CLI verifies
and replays the existing frozen model caches, rather than promising a fresh-data bootstrap.

## Install and run without market data

From the repository root on Linux/WSL with Python 3.13:

```bash
python -m pip install -r requirements/research-runtime-py313.txt
python -m pip install -e ".[research,dev]"
python -m momentum_data --help
python -m momentum_data smoke
python -m pytest tests -q
```

The smoke example creates a synthetic cross-year position and verifies its cash
and Funding. It requires no API key, exchange connection or market dataset and
makes no profitability claim. Runtime pins cover the current top-level packages,
not a fully transitive environment lock. Historical lockfiles are retained separately.

## Reproduce saved results

With the existing ignored local dataset and frozen caches available:

```bash
python -m momentum_data verify
python -m momentum_data replay
python -m momentum_data summary
python -m momentum_data publish
```

`replay` runs both cost cases and the primary replay through the reorganized engine
in a separate output directory; every financial SHA256 must equal the frozen result.
It never overwrites the original case files. The new package also binds its own
source/configuration contract. Local paths default to this checkout; set
`MOMENTUM_PROJECT_ROOT` and, if needed, `MOMENTUM_DATA_ROOT` before importing the
package to point at another research checkout/data root.

The original convenience commands remain available:

```bash
conda activate funding-strategy
python scripts/run_continuous_reconstruction.py --stage all
python scripts/run_continuous_reconstruction.py --stage summary
python scripts/publish_continuous_results.py
```

The publisher reads verified outputs; it performs no refit, download or simulation.
Full simulator runs require the ignored local research data and frozen caches; this
repository alone does not supply a one-command fresh-data bootstrap. Never add keys
or market datasets to Git, or delete contracts to bypass validation failures.

- [Results, annual/monthly detail and source provenance](docs/CONTINUOUS_RECONSTRUCTION_RESULTS.md)
- [Simulation runbook, logs and resume behavior](docs/CONTINUOUS_RECONSTRUCTION_RUNBOOK.md)
- [English saved-results notebook](notebooks/continuous_reconstruction_results.ipynb)
- [Experiment 016 registration](experiments/016_continuous_2022_2026.md)
- [Project status / handoff](docs/PROJECT_STATUS.md)

`experiments/` holds registrations; `scripts/` contains thin launchers; `src/`
holds the independent package; `tests/` current accounting/interface checks; `docs/`
methodology and conclusions. Source datasets and generated working reports remain
ignored; this README and its figure publish aggregate results only.

## Research archive

{archive}
""",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "success": True,
                "verified_months": len(returns),
                "positive_months": positive,
                "median_month": float(returns.median()),
                "return_2024_onward": float(since2024.loc["strategy_nav", "total_return"]),
                "figure": str(IMAGE),
                "results": str(DETAILS),
                "README": str(readme),
                "strategy_or_model_changed": False,
            }
        )
    )


if __name__ == "__main__":
    publish()
