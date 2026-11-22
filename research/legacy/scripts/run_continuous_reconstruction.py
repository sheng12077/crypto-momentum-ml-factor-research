"""Logged, resumable continuous Nautilus reconstruction; user runs historical PnL."""
import argparse
import fcntl
import json
import shutil
import sys
import traceback
from datetime import UTC, datetime
from decimal import Decimal as D

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from continuous_reconstruction import (BASE, ROOT, PREPARED, START, STOP, DAY, HOUR,
    YEARS, FEATURES, MODEL_ROOTS, ContinuousData, contract, preflight, write, sha, checked_manifest)
from final_holdout_engine import simulate
from first_development_engine import Money, USDT
sys.path.insert(0, str(ROOT / "src"))
from momentum_data.backtest_analysis import performance_tables, plot_development, validate_daily

TABLES = ROOT / "reports/tables/continuous_reconstruction"
FIGURES = ROOT / "reports/figures/continuous_reconstruction"
PRODUCTS = ["engine_daily.csv", "fills.csv", "funding.csv", "targets.csv", "engine_summary.json", "daily.csv", "audit.json"]


def ledger(folder, name):
    try:
        return pd.read_csv(folder / (name+".csv"), dtype=str)
    except pd.errors.EmptyDataError:
        cols = {"fills": ["timestamp_ns", "instrument_id", "side", "quantity", "price", "commission_usdt", "notional_usdt"],
                "funding": ["timestamp_ns", "instrument_id", "signed_quantity", "cashflow_usdt"]}
        return pd.DataFrame(columns=cols[name])


def audit_case(data, folder, bps, start=START, stop=STOP):
    """Reconstruct funding positions independently from fills, including cross-year fills."""
    fills, funding = ledger(folder, "fills"), ledger(folder, "funding")
    final = (stop-DAY-HOUR)*1000000
    for row in fills.itertuples():
        ns = int(row.timestamp_ns)
        hour = (ns//1000000//HOUR) % 24
        if ns < start*1000000 or ns > final or (hour != 2 and ns != final):
            raise ValueError("Intermediate liquidation or invalid fill time")
        vwap = data.vwap(row.instrument_id, ns//1000000-HOUR)
        sign = 1 if row.side == "BUY" else -1
        if vwap is None or abs(round(vwap*(1+sign*bps/10000), 8)-float(row.price)) > 1.1e-8:
            raise ValueError("Source execution price/slippage mismatch")
        fee = D(row.price)*D(row.quantity)*D("0.0005")
        if abs(fee-D(row.commission_usdt)) > D("0.000001"):
            raise ValueError("Perpetual fee mismatch")
    recorded = {(r.instrument_id, int(r.timestamp_ns)): r for r in funding.itertuples()}
    if len(recorded) != len(funding):
        raise ValueError("Duplicate funding cashflow")
    matched = set()
    for symbol in data.symbols:
        subset = fills[fills.instrument_id == symbol].copy()
        rows = sorted((int(r.timestamp_ns), D(r.quantity)*(1 if r.side == "BUY" else -1)) for r in subset.itertuples())
        cursor, position = 0, D(0)
        for t, rate in data.funding.get(symbol, []):
            if not start <= t <= stop-DAY:
                continue
            ns = t*1000000
            while cursor < len(rows) and rows[cursor][0] < ns:
                position += rows[cursor][1]
                cursor += 1
            key = symbol, ns
            row = recorded.get(key)
            if not position:
                if row is not None:
                    raise ValueError("Funding charged while flat")
                continue
            mark = data.mark(symbol, t)
            if row is None or mark is None or int(row.mark_available_ms) != mark[1]:
                raise ValueError(f"Missing held funding/mark: {symbol}/{t}")
            expected = Money(-position*D(str(mark[0]))*D(str(rate)), USDT).as_decimal()
            if (abs(position-D(row.signed_quantity)) > D("0.000001") or
                abs(float(row.mark_proxy)-mark[0]) > 1e-8 or
                abs(expected-D(row.cashflow_usdt)) > D("0.000001")):
                raise ValueError("Independent funding amount/quantity mismatch")
            matched.add(key)
    if matched != set(recorded):
        raise ValueError("Unexpected funding cashflows")
    daily = pd.read_csv(folder / "engine_daily.csv")
    expected_dates = pd.date_range(pd.Timestamp(start, unit="ms", tz="UTC"), pd.Timestamp(stop-DAY, unit="ms", tz="UTC"), freq="D")
    if not pd.DatetimeIndex(pd.to_datetime(daily.timestamp, utc=True)).equals(expected_dates):
        raise ValueError("Incomplete continuous daily calendar")
    if daily.strategy_nav.iloc[0] != 100000 or not np.allclose(daily.strategy_nav, daily.cash_usdt+daily.unrealized_usdt, atol=.01, rtol=0):
        raise ValueError("NAV reconciliation failed")
    for col, rows, amount in [("commissions_usdt", fills, "commission_usdt"),
                               ("funding_cashflow_usdt", funding, "cashflow_usdt"),
                               ("traded_notional_usdt", fills, "notional_usdt")]:
        if abs(daily[col].sum()-pd.to_numeric(rows[amount]).sum()) > .001:
            raise ValueError("Daily ledger totals disagree")
    engine = json.loads((folder / "engine_summary.json").read_text())
    if not engine["success"] or abs(engine["ledger_error_usdt"]) > .01:
        raise ValueError("Engine ending ledger mismatch")
    for symbol, col in (("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")):
        ref = pd.read_csv(BASE / f"{symbol}_spot.csv")
        if not ref.timestamp.equals(daily.timestamp):
            raise ValueError("Benchmark period mismatch")
        daily[col] = ref.strategy_nav
    validate_daily(daily)
    daily.to_csv(folder / "daily.csv", index=False)
    result = {"success": True, "verified_fills": len(fills), "verified_funding_rows": len(funding),
              "daily_snapshots": len(daily), "intermediate_final_fills": 0,
              "financial_sha256": engine["financial_sha256"]}
    write(folder / "audit.json", result)
    return result


def require_preflight():
    if json.loads((BASE / "contract.json").read_text()) != contract():
        raise ValueError("Code/input contract changed; preserve outputs and investigate")
    meta = checked_manifest(BASE, "preflight_complete.json")
    if meta["contract_sha256"] != sha(BASE / "contract.json"):
        raise ValueError("Preflight contract mismatch")


def case(data, events, plan, name, bps):
    folder = BASE / "results" / name
    if (folder / "_complete.json").exists():
        meta = checked_manifest(folder, "_complete.json")
        if meta["contract_sha256"] != sha(BASE / "contract.json") or meta["slippage_bps"] != bps:
            raise ValueError("Case cache contract mismatch")
        return meta
    attempt = folder / "attempts" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True)
    write(attempt / "attempt.json", {"case": name, "slippage_bps": bps, "contract_sha256": sha(BASE / "contract.json")})
    simulate(data, events, plan, attempt, bps=bps)
    audit = audit_case(data, attempt, bps)
    for product in PRODUCTS:
        shutil.copyfile(attempt / product, folder / product)
    meta = {"success": True, "slippage_bps": bps, "contract_sha256": sha(BASE / "contract.json"),
            "financial_sha256": audit["financial_sha256"], "output_hashes": {n: sha(folder / n) for n in PRODUCTS}}
    write(folder / "_complete.json", meta)
    return meta


def simulate_all():
    require_preflight()
    data = ContinuousData(PREPARED)
    events = data.events_range(START, STOP-DAY)
    plan = json.loads((BASE / "schedule.json").read_text())
    completed = {}
    for name, bps in (("slippage_5bps", 5), ("slippage_10bps", 10), ("primary_replay", 5)):
        print(f"Nautilus continuous 2022--2026: {name}", flush=True)
        completed[name] = case(data, events, plan, name, bps)
    if completed["slippage_5bps"]["financial_sha256"] != completed["primary_replay"]["financial_sha256"]:
        raise ValueError("Continuous primary replay differs")
    require_preflight()
    write(BASE / "simulation_complete.json", {"success": True, "financial_cases": 2, "verified_replays": 1,
        "new_model_fits": 0, "annual_cash_resets": 0, "cases": completed,
        "output_hashes": {f"results/{n}/_complete.json": sha(BASE / f"results/{n}/_complete.json") for n in completed}})


def year_slices(daily):
    """Include the return ending January 1 in its new calendar year."""
    frames = []
    for year in YEARS:
        first = pd.Timestamp(f"{year}-01-01", tz="UTC")
        base = max(daily.index[0], first-pd.Timedelta(days=1))
        last = min(daily.index[-1], pd.Timestamp(f"{year}-12-31", tz="UTC"))
        subset = daily.loc[base:last]
        metric, _ = performance_tables(subset)
        metric = metric.reset_index()
        metric["year"] = year
        metric["start_nav_timestamp"] = str(base)
        metric["end_nav_timestamp"] = str(last)
        frames.append(metric)
    return pd.concat(frames, ignore_index=True)


def economic_gates(primary, stress, other_months):
    strategy = primary.loc["strategy_nav"]
    benchmarks = primary.loc[["btc_nav", "eth_nav"]]
    return {"positive_net_return_and_sharpe": bool(strategy.total_return > 0 and strategy.Sharpe_rf0 > 0),
            "positive_10bps_stress_return": bool(stress.loc["strategy_nav", "total_return"] > 0),
            "sharpe_above_both_spot_benchmarks": bool((strategy.Sharpe_rf0 > benchmarks.Sharpe_rf0).all()),
            "smaller_MDD_than_both_spot_benchmarks": bool((abs(strategy.MDD) < benchmarks.MDD.abs()).all()),
            "positive_return_excluding_best_month": bool(other_months > 0)}


def report():
    require_preflight()
    checked_manifest(BASE, "simulation_complete.json")
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    metrics_by_case = {}
    data = ContinuousData(PREPARED)
    for name, bps in (("slippage_5bps", 5), ("slippage_10bps", 10), ("primary_replay", 5)):
        checked_manifest(BASE / "results" / name, "_complete.json")
        # Repeat the independent source audit even for resumed cached results.
        audit_case(data, BASE / "results" / name, bps)
    for bps in (5, 10):
        folder = BASE / f"results/slippage_{bps}bps"
        daily = validate_daily(pd.read_csv(folder / "daily.csv"))
        fig, metrics, monthly = plot_development(daily)
        fig.suptitle(f"2022--October 2026 CONTINUOUS RECONSTRUCTION | {bps} bps slippage | retrospective, not fresh OOS")
        fig.savefig(FIGURES / f"dashboard_{bps}bps.png", dpi=130)
        plt.close(fig)
        metrics.to_csv(TABLES / f"metrics_{bps}bps.csv")
        monthly.to_csv(TABLES / f"monthly_returns_{bps}bps.csv")
        year_slices(daily).to_csv(TABLES / f"year_slices_{bps}bps.csv", index=False)
        daily.to_csv(TABLES / f"daily_{bps}bps.csv")
        metrics_by_case[bps] = metrics
        if bps == 5:
            primary_daily, primary_monthly = daily, monthly
    # Show cash/equity across each boundary; no annual rebasing or missing bridge day.
    bridge = primary_daily[(primary_daily.index.month == 1) & (primary_daily.index.day <= 2) |
                           (primary_daily.index.month == 12) & (primary_daily.index.day >= 30)]
    bridge.to_csv(TABLES / "year_boundaries.csv")
    best = primary_monthly.strategy_nav.idxmax()
    other = float((1+primary_monthly.strategy_nav.drop(best)).prod()-1)
    cash_month = primary_daily.strategy_nav.diff().fillna(0).resample(pd.offsets.MonthEnd()).sum()
    total_cash = float(cash_month.sum())
    # Annual cached SHAP remains model attribution, not causal profit attribution.
    fig, axes = plt.subplots(1, 5, figsize=(19, 4), layout="constrained")
    for ax, year in zip(axes, YEARS):
        shap = pd.read_csv(MODEL_ROOTS[year] / "shap_values.csv")
        shap[["shap_"+f for f in FEATURES]].abs().mean().rename(index=lambda x: x[5:]).sort_values().plot.barh(ax=ax)
        ax.set(title=str(year), xlabel="Mean absolute SHAP")
    fig.suptitle("Cached annual models: prediction attribution, not causal PnL")
    fig.savefig(FIGURES / "annual_shap.png", dpi=130)
    plt.close(fig)
    summary = {"success": True, "report_verified": True, "financial_cases": 2, "verified_replays": 1,
        "new_model_fits": 0, "annual_cash_resets": 0, "fresh_OOS": False, "paper_or_live_ready": False,
        "initial_nav": 100000, "ending_nav": float(primary_daily.strategy_nav.iloc[-1]),
        "period": [str(primary_daily.index[0]), str(primary_daily.index[-1])],
        "evidence_gates": economic_gates(metrics_by_case[5], metrics_by_case[10], other),
        "best_month": str(best), "other_months_compounded_return": other,
        "best_month_cash_profit_share": float(cash_month.loc[best]/total_cash) if total_cash > 0 else None,
        "primary_results": metrics_by_case[5].reset_index().to_dict("records"),
        "stress_strategy_results": metrics_by_case[10].loc["strategy_nav"].to_dict(),
        "fees_usdt": float(primary_daily.commissions_usdt.sum()),
        "funding_usdt": float(primary_daily.funding_cashflow_usdt.sum()),
        "gross_traded_notional_usdt": float(primary_daily.traded_notional_usdt.sum()),
        "limitations": ["Retrospective 37-asset conditional cohort; publication vintage not proven",
            "Development and previously inspected years; no fresh OOS",
            "Historical lot/margin/liquidation rules not certified; hourly execution/funding mark proxies",
            "Momentum-only comparison excluded due to unverified EOS settlement; no alpha claim"],
        "contract_sha256": sha(BASE / "contract.json"),
        "output_hashes": {str(p.relative_to(BASE)): sha(p) for p in [BASE / "simulation_complete.json"]}}
    artifacts = [*TABLES.glob("*.csv"), *FIGURES.glob("*.png")]
    write(BASE / "report_complete.json", {"success": True, "output_hashes": {str(p.relative_to(ROOT)): sha(p) for p in artifacts}})
    summary["report_manifest_sha256"] = sha(BASE / "report_complete.json")
    write(BASE / "summary.json", summary)
    print_summary()


def print_summary():
    path = BASE / "summary.json"
    if not path.exists():
        print(json.dumps({"success": False, "completed": False, "preflight_complete": (BASE / "preflight_complete.json").exists(),
            "completed_cases": len(list((BASE / "results").glob("*/_complete.json"))), "output": str(BASE)}))
        return
    obj = json.loads(path.read_text())
    require_preflight()
    checked_manifest(BASE, "simulation_complete.json")
    for name in ("slippage_5bps", "slippage_10bps", "primary_replay"):
        checked_manifest(BASE / "results" / name, "_complete.json")
    report_meta = json.loads((BASE / "report_complete.json").read_text())
    if sha(BASE / "report_complete.json") != obj["report_manifest_sha256"] or any(sha(ROOT / p) != h for p, h in report_meta["output_hashes"].items()):
        raise ValueError("Report artifacts changed")
    print(json.dumps({k: obj[k] for k in ("success", "report_verified", "financial_cases", "verified_replays", "new_model_fits",
        "annual_cash_resets", "fresh_OOS", "evidence_gates", "primary_results", "stress_strategy_results", "other_months_compounded_return")}))


class Tee:
    def __init__(self, stream, log):
        self.stream, self.log = stream, log
    def write(self, text):
        self.stream.write(text)
        self.log.write(text)
        self.log.flush()
    def flush(self):
        self.stream.flush()
        self.log.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["all", "preflight", "simulate", "report", "summary"], default="all")
    args = parser.parse_args()
    if args.stage == "summary":
        print_summary()
        return
    BASE.mkdir(parents=True, exist_ok=True)
    with (BASE / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another continuous reconstruction is running")
        log = ROOT / f"reports/acquisition/continuous_{args.stage}_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        print(f"Log: {log}", flush=True)
        stdout, stderr = sys.stdout, sys.stderr
        with log.open("w") as handle:
            sys.stdout, sys.stderr = Tee(stdout, handle), Tee(stderr, handle)
            try:
                for stage in (["preflight", "simulate", "report"] if args.stage == "all" else [args.stage]):
                    {"preflight": preflight, "simulate": simulate_all, "report": report}[stage]()
            except Exception as exc:
                write(BASE / "last_failure.json", {"success": False, "failed_stage": stage, "error": str(exc), "log": str(log)})
                traceback.print_exc()
                raise SystemExit(1)
            finally:
                sys.stdout, sys.stderr = stdout, stderr


if __name__ == "__main__":
    main()
