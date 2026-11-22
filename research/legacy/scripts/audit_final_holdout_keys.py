"""Read-only timestamp/lifecycle key audit; no features, rankings, PnL or HTTP."""
import json

from final_holdout_common import OLD, ROOT, months
from final_holdout_lifecycle import filter_terminal_rows, terminal_boundaries
from prepare_first_development import DAILY, load_hours


def main():
    symbols = json.loads((OLD / "manifest.json").read_text())["symbols"]
    boundaries = terminal_boundaries(symbols)
    rows = []
    for i, symbol in enumerate(symbols, 1):
        index = json.loads((DAILY / "index" / f"{symbol}.json").read_text())
        products = {k: [] for k in ("trade", "mark")}
        for kind in products:
            for month in months():
                products[kind] += load_hours(symbol, kind, month, index, False, {})
        try:
            filtered, audit = filter_terminal_rows(symbol, products, boundaries.get(symbol))
            t = {r["bar_open_ms"] for r in filtered["trade"]}
            m = {r["bar_open_ms"] for r in filtered["mark"]}
            row = {"symbol": symbol, "active_missing_trade": len(m-t), "active_missing_mark": len(t-m),
                   "first_missing_trade_ms": min(m-t) if m-t else None,
                   "first_missing_mark_ms": min(t-m) if t-m else None, "quarantined": audit["quarantined"]}
        except ValueError as exc:
            row = {"symbol": symbol, "error": str(exc)}
        rows.append(row)
        print(f"key audit {i}/{len(symbols)} {symbol}", flush=True)
    unresolved = [r for r in rows if r.get("error") or r.get("active_missing_trade", 0) or r.get("active_missing_mark", 0)]
    report = {"success": not unresolved, "scope": "timestamp/source availability; no features/models/PnL",
              "identifiers": len(rows), "rows": rows, "new_http_requests": 0, "historical_simulations": 0}
    path = ROOT / "reports/acquisition/final_holdout_terminal_key_audit_20261122.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"success": not unresolved, "identifiers": len(rows), "unresolved": unresolved, "report": str(path)}))
    if unresolved:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
