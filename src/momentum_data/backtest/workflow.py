"""Public frozen-artifact reader and independently checked package replay."""

import json
import shutil
from datetime import UTC, datetime
from decimal import Decimal as D
import numpy as np
import pandas as pd
from ..settings import BASE, ROOT, PREPARED, START, STOP, DAY, HOUR, YEARS, PACKAGE_OUTPUT
from ..integrity import sha, write, bind, checked_manifest, verify_frozen_contract, package_contract
from ..data.historical import ContinuousData
from ..data.preflight import verify_inputs
from .engine import simulate, Money, USDT
from ..reporting.analysis import validate_daily, performance_tables

TABLES = ROOT / "reports/tables/continuous_reconstruction"
FIGURES = ROOT / "reports/figures/continuous_reconstruction"
PRODUCTS = [
    "engine_daily.csv",
    "fills.csv",
    "funding.csv",
    "targets.csv",
    "engine_summary.json",
    "daily.csv",
    "audit.json",
]


def ledger(folder, name):
    try:
        return pd.read_csv(folder / (name + ".csv"), dtype=str)
    except pd.errors.EmptyDataError:
        cols = {
            "fills": [
                "timestamp_ns",
                "instrument_id",
                "side",
                "quantity",
                "price",
                "commission_usdt",
                "notional_usdt",
            ],
            "funding": ["timestamp_ns", "instrument_id", "signed_quantity", "cashflow_usdt"],
        }
        return pd.DataFrame(columns=cols[name])


def audit_case(data, folder, bps, start=START, stop=STOP):
    """Reconstruct funding positions independently from fills, including cross-year fills."""
    fills, funding = ledger(folder, "fills"), ledger(folder, "funding")
    final = (stop - DAY - HOUR) * 1000000
    for row in fills.itertuples():
        ns = int(row.timestamp_ns)
        hour = (ns // 1000000 // HOUR) % 24
        if ns < start * 1000000 or ns > final or (hour != 2 and ns != final):
            raise ValueError("Intermediate liquidation or invalid fill time")
        vwap = data.vwap(row.instrument_id, ns // 1000000 - HOUR)
        sign = 1 if row.side == "BUY" else -1
        if (
            vwap is None
            or abs(round(vwap * (1 + sign * bps / 10000), 8) - float(row.price)) > 1.1e-8
        ):
            raise ValueError("Source execution price/slippage mismatch")
        fee = D(row.price) * D(row.quantity) * D("0.0005")
        if abs(fee - D(row.commission_usdt)) > D("0.000001"):
            raise ValueError("Perpetual fee mismatch")
    recorded = {(r.instrument_id, int(r.timestamp_ns)): r for r in funding.itertuples()}
    if len(recorded) != len(funding):
        raise ValueError("Duplicate funding cashflow")
    matched = set()
    for symbol in data.symbols:
        subset = fills[fills.instrument_id == symbol].copy()
        rows = sorted(
            (int(r.timestamp_ns), D(r.quantity) * (1 if r.side == "BUY" else -1))
            for r in subset.itertuples()
        )
        cursor, position = 0, D(0)
        for t, rate in data.funding.get(symbol, []):
            if not start <= t <= stop - DAY:
                continue
            ns = t * 1000000
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
            expected = Money(-position * D(str(mark[0])) * D(str(rate)), USDT).as_decimal()
            if (
                abs(position - D(row.signed_quantity)) > D("0.000001")
                or abs(float(row.mark_proxy) - mark[0]) > 1e-8
                or abs(expected - D(row.cashflow_usdt)) > D("0.000001")
            ):
                raise ValueError("Independent funding amount/quantity mismatch")
            matched.add(key)
    if matched != set(recorded):
        raise ValueError("Unexpected funding cashflows")
    daily = pd.read_csv(folder / "engine_daily.csv")
    expected_dates = pd.date_range(
        pd.Timestamp(start, unit="ms", tz="UTC"),
        pd.Timestamp(stop - DAY, unit="ms", tz="UTC"),
        freq="D",
    )
    if not pd.DatetimeIndex(pd.to_datetime(daily.timestamp, utc=True)).equals(expected_dates):
        raise ValueError("Incomplete continuous daily calendar")
    if daily.strategy_nav.iloc[0] != 100000 or not np.allclose(
        daily.strategy_nav, daily.cash_usdt + daily.unrealized_usdt, atol=0.01, rtol=0
    ):
        raise ValueError("NAV reconciliation failed")
    for col, rows, amount in [
        ("commissions_usdt", fills, "commission_usdt"),
        ("funding_cashflow_usdt", funding, "cashflow_usdt"),
        ("traded_notional_usdt", fills, "notional_usdt"),
    ]:
        if abs(daily[col].sum() - pd.to_numeric(rows[amount]).sum()) > 0.001:
            raise ValueError("Daily ledger totals disagree")
    engine = json.loads((folder / "engine_summary.json").read_text())
    if not engine["success"] or abs(engine["ledger_error_usdt"]) > 0.01:
        raise ValueError("Engine ending ledger mismatch")
    for symbol, col in (("BTCUSDT", "btc_nav"), ("ETHUSDT", "eth_nav")):
        ref = pd.read_csv(BASE / f"{symbol}_spot.csv")
        if not ref.timestamp.equals(daily.timestamp):
            raise ValueError("Benchmark period mismatch")
        daily[col] = ref.strategy_nav
    validate_daily(daily)
    daily.to_csv(folder / "daily.csv", index=False)
    result = {
        "success": True,
        "verified_fills": len(fills),
        "verified_funding_rows": len(funding),
        "daily_snapshots": len(daily),
        "intermediate_final_fills": 0,
        "financial_sha256": engine["financial_sha256"],
    }
    write(folder / "audit.json", result)
    return result


def year_slices(daily):
    """Include the return ending January 1 in its new calendar year."""
    frames = []
    for year in YEARS:
        first = pd.Timestamp(f"{year}-01-01", tz="UTC")
        base = max(daily.index[0], first - pd.Timedelta(days=1))
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
    return {
        "positive_net_return_and_sharpe": bool(
            strategy.total_return > 0 and strategy.Sharpe_rf0 > 0
        ),
        "positive_10bps_stress_return": bool(stress.loc["strategy_nav", "total_return"] > 0),
        "sharpe_above_both_spot_benchmarks": bool(
            (strategy.Sharpe_rf0 > benchmarks.Sharpe_rf0).all()
        ),
        "smaller_MDD_than_both_spot_benchmarks": bool(
            (abs(strategy.MDD) < benchmarks.MDD.abs()).all()
        ),
        "positive_return_excluding_best_month": bool(other_months > 0),
    }


def print_summary():
    path = BASE / "summary.json"
    if not path.exists():
        print(
            json.dumps(
                {
                    "success": False,
                    "completed": False,
                    "preflight_complete": (BASE / "preflight_complete.json").exists(),
                    "completed_cases": len(list((BASE / "results").glob("*/_complete.json"))),
                    "output": str(BASE),
                }
            )
        )
        return
    obj = json.loads(path.read_text())
    require_preflight()
    checked_manifest(BASE, "simulation_complete.json")
    for name in ("slippage_5bps", "slippage_10bps", "primary_replay"):
        checked_manifest(BASE / "results" / name, "_complete.json")
    report_meta = json.loads((BASE / "report_complete.json").read_text())
    if sha(BASE / "report_complete.json") != obj["report_manifest_sha256"] or any(
        sha(ROOT / p) != h for p, h in report_meta["output_hashes"].items()
    ):
        raise ValueError("Report artifacts changed")
    print(
        json.dumps(
            {
                k: obj[k]
                for k in (
                    "success",
                    "report_verified",
                    "financial_cases",
                    "verified_replays",
                    "new_model_fits",
                    "annual_cash_resets",
                    "fresh_OOS",
                    "evidence_gates",
                    "primary_results",
                    "stress_strategy_results",
                    "other_months_compounded_return",
                )
            }
        )
    )


def require_preflight():
    verify_frozen_contract(BASE)
    meta = checked_manifest(BASE, "preflight_complete.json")
    if meta["contract_sha256"] != sha(BASE / "contract.json"):
        raise ValueError("Frozen preflight contract mismatch")


def case(data, events, plan, name, bps):
    folder = PACKAGE_OUTPUT / "results" / name
    if (folder / "_complete.json").exists():
        meta = checked_manifest(folder, "_complete.json")
        if meta["contract_sha256"] != sha(BASE / "contract.json") or meta["slippage_bps"] != bps:
            raise ValueError("Case cache contract mismatch")
        return meta
    attempt = folder / "attempts" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True)
    write(
        attempt / "attempt.json",
        {"case": name, "slippage_bps": bps, "contract_sha256": sha(BASE / "contract.json")},
    )
    simulate(data, events, plan, attempt, bps=bps)
    audit = audit_case(data, attempt, bps)
    for product in PRODUCTS:
        shutil.copyfile(attempt / product, folder / product)
    meta = {
        "success": True,
        "slippage_bps": bps,
        "contract_sha256": sha(BASE / "contract.json"),
        "financial_sha256": audit["financial_sha256"],
        "output_hashes": {n: sha(folder / n) for n in PRODUCTS},
    }
    write(folder / "_complete.json", meta)
    return meta


def _replay_unlocked():
    """All cases use the new engine, separate outputs, and must match frozen financial hashes."""
    data, events, plan, preflight = verify_inputs()
    bind(PACKAGE_OUTPUT / "package_contract.json", package_contract())
    results = {}
    for name, bps in (("slippage_5bps", 5), ("slippage_10bps", 10), ("primary_replay", 5)):
        print(f"Package replay: {name}", flush=True)
        result = case(data, events, plan, name, bps)
        expected = checked_manifest(BASE / "results" / name, "_complete.json")
        if result["financial_sha256"] != expected["financial_sha256"]:
            raise ValueError(f"Refactoring changed financial output: {name}")
        results[name] = result["financial_sha256"]
    if results["slippage_5bps"] != results["primary_replay"]:
        raise ValueError("Package primary replay differs")
    write(
        PACKAGE_OUTPUT / "verification.json",
        {
            "success": True,
            "financial_cases_identical": 3,
            "new_model_fits": 0,
            "frozen_contract_sha256": sha(BASE / "contract.json"),
            "package_contract_sha256": sha(PACKAGE_OUTPUT / "package_contract.json"),
            "financial_hashes": results,
        },
    )
    print(
        json.dumps({"success": True, "financial_cases_identical": 3, "output": str(PACKAGE_OUTPUT)})
    )


def replay():
    """Hold a process lock and keep a complete log for every reproduction attempt."""
    import contextlib
    import fcntl
    import traceback

    PACKAGE_OUTPUT.mkdir(parents=True, exist_ok=True)
    log = PACKAGE_OUTPUT / ("replay_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".log")
    with (PACKAGE_OUTPUT / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another package replay is running") from None
        print(f"Log: {log}", flush=True)
        with log.open("w") as handle:
            # Keep terminal progress concise; the complete Python traceback goes to this log.
            try:
                _replay_unlocked()
                handle.write("All three financial hashes matched the original frozen cases.\n")
            except Exception:
                traceback.print_exc(file=handle)
                raise
