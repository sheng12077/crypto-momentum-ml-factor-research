"""Independent source/quantity/fee checks on every completed final-holdout case."""
import json
from decimal import Decimal as D

import pandas as pd
from audit_development_continuity import sha
from final_holdout_common import BASE, DAY, HOUR, PREPARED, ROOT, WINDOWS, checked_manifest
from final_holdout_engine import FinalHistoricalData
from first_development_engine import Money, USDT


def main():
    results = BASE / "results"
    source = FinalHistoricalData(PREPARED)
    table = pd.read_csv(results / "all_runs.csv")
    reports = []
    for case in table.itertuples():
        folder = results / f"{case.window}/{case.model}/slippage_{case.slippage_bps}bps"
        checked_manifest(folder, "_complete.json")
        fills = pd.read_csv(folder / "fills.csv", dtype=str)
        funding = pd.read_csv(folder / "funding.csv", dtype=str)
        funding_map = {(r.instrument_id, int(r.timestamp_ns)): r for r in funding.itertuples()}
        if len(funding_map) != len(funding):
            raise ValueError("Duplicate recorded funding")
        matched = set()
        max_price_error = max_cash_error = max_qty_error = 0.
        for row in fills.itertuples():
            vwap = source.vwap(row.instrument_id, int(row.timestamp_ns)//1000000-HOUR)
            if vwap is None:
                raise ValueError("Fill missing source VWAP")
            sign = 1 if row.side == "BUY" else -1
            expected_price = round(vwap*(1+sign*case.slippage_bps/10000), 8)
            error = abs(expected_price-float(row.price))
            max_price_error = max(max_price_error, error)
            if error > 1.1e-8:
                raise ValueError("Fill differs from source/slippage")
            fee = D(row.price)*D(row.quantity)*D("0.0005")
            if abs(fee-D(row.commission_usdt)) > D("0.000001"):
                raise ValueError("Fee differs from frozen taker schedule")
        start, stop = WINDOWS[case.window]
        for symbol in source.symbols:
            group = fills[fills.instrument_id == symbol].sort_values("timestamp_ns")
            trades = [(int(r.timestamp_ns), D(r.quantity)*(1 if r.side == "BUY" else -1)) for r in group.itertuples()]
            cursor, position = 0, D(0)
            for stamp, rate in source.funding.get(symbol, []):
                if not start <= stamp <= stop-DAY:
                    continue
                ns = stamp*1000000
                while cursor < len(trades) and trades[cursor][0] < ns:
                    position += trades[cursor][1]
                    cursor += 1
                key = symbol, ns
                row = funding_map.get(key)
                if not position:
                    if row is not None:
                        raise ValueError("Funding charged to a flat position")
                    continue
                if row is None:
                    raise ValueError(f"Missing held funding cashflow: {symbol}/{ns}")
                mark = source.mark(symbol, stamp)
                if mark is None or int(row.mark_available_ms) != mark[1] or abs(float(row.mark_proxy)-mark[0]) > 1e-8:
                    raise ValueError("Funding mark differs from completed source mark")
                qty_error = abs(position-D(row.signed_quantity))
                max_qty_error = max(max_qty_error, float(qty_error))
                expected = Money(-position*D(str(mark[0]))*D(str(rate)), USDT).as_decimal()
                error = abs(expected-D(row.cashflow_usdt))
                max_cash_error = max(max_cash_error, float(error))
                if qty_error > D("0.000001") or error > D("0.000001"):
                    raise ValueError("Funding quantity/cashflow differs from independent reconstruction")
                matched.add(key)
        if matched != set(funding_map):
            raise ValueError("Unexpected funding cashflows")
        reports.append({"window": case.window, "model": case.model, "slippage_bps": case.slippage_bps,
            "fills_verified": len(fills), "funding_rows_verified": len(funding),
            "max_fill_price_error": max_price_error, "max_funding_cash_error": max_cash_error,
            "max_quantity_error": max_qty_error})
    previous = BASE.parent / "v20261122_002/results/models"
    for year in (2025, 2026):
        meta = checked_manifest(results / f"models/{year}", "model_summary.json")
        for name, digest in meta["output_hashes"].items():
            if sha(previous / str(year) / name) != digest:
                raise ValueError("Cached model/input/prediction changed during reuse")
    report = {"success": True, "verified_cases": len(reports), "new_model_fits": 0,
        "original_models_predictions_unchanged": True, "cases": reports,
        "total_fills_verified": sum(r["fills_verified"] for r in reports),
        "total_funding_rows_verified": sum(r["funding_rows_verified"] for r in reports)}
    path = ROOT / "reports/acquisition/final_holdout_execution_audit_20261122.json"
    path.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}))


if __name__ == "__main__":
    main()
