"""Proven terminal boundaries: quarantine archive tails, never synthesize settlement."""
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from audit_development_continuity import sha
from final_holdout_common import HOUR, ROOT, write
from review_usdm_lifecycle import text_nodes

REVIEW = ROOT / "data/interim/usdm_universe/lifecycle_review_20261118"


def terminal_boundaries(symbols, review=REVIEW):
    meta = json.loads((review / "summary.json").read_text())
    if sha(review / "events.json") != meta["events_sha256"]:
        raise ValueError("Lifecycle evidence ledger changed")
    out = {}
    for event in json.loads((review / "events.json").read_text()):
        symbol = event["instrument_id"]
        if symbol not in symbols or event["event_type"] != "automatic_settlement":
            continue
        source = event["source"]
        raw = review / "sources" / (source["article_code"]+".raw")
        if sha(raw) != source["sha256"]:
            raise ValueError("Lifecycle official source changed")
        article = json.loads(raw.read_bytes())["data"]
        text = " ".join(text_nodes(json.loads(article["body"])))
        if any(term.casefold() not in text.casefold() for term in event["evidence_terms"]):
            raise ValueError("Lifecycle source terms not corroborated")
        stamp = datetime.fromisoformat(event["effective_at"])
        if stamp.utcoffset().total_seconds() != 0:
            raise ValueError("Lifecycle boundary must be UTC")
        value = {"effective_ms": int(stamp.timestamp()*1000), "event_id": event["event_id"],
                 "source_sha256": source["sha256"], "source_url": source["source_url"],
                 "historical_publication_vintage_proven": False}
        if symbol in out and out[symbol]["effective_ms"] != value["effective_ms"]:
            raise ValueError(f"Multiple terminal episodes need explicit review: {symbol}")
        out[symbol] = value
    return out


def filter_terminal_rows(symbol, products, boundary):
    if boundary is None:
        return products, {"terminal_boundary": None, "quarantined": {k: 0 for k in products}}
    end = boundary["effective_ms"]
    out, counts = {}, {}
    for kind, rows in products.items():
        key = "event_timestamp_ms" if kind == "funding" else "bar_open_ms"
        # A terminal-hour bucket can contain settlement prints; it is quarantined,
        # never a full tradable bar. Later positive full-hour buckets need review.
        if kind == "trade" and any(r[key] >= (end//HOUR+1)*HOUR and r["volume"] > 0 for r in rows):
            raise ValueError(f"Positive trades after proven terminal boundary need episode review: {symbol}")
        keep = [r for r in rows if r[key] < end and (kind == "funding" or r[key]+HOUR <= end)]
        out[kind], counts[kind] = keep, len(rows)-len(keep)
    return out, {"terminal_boundary": boundary, "quarantined": counts}


def repair_pair(symbol, trades, marks, repair, audit_folder):
    maps = {"trade": {r["bar_open_ms"]: r for r in trades}, "mark": {r["bar_open_ms"]: r for r in marks}}
    if len(maps["trade"]) != len(trades) or len(maps["mark"]) != len(marks):
        raise ValueError(f"Duplicate hourly keys: {symbol}")
    repaired_days, counts = set(), {}
    for kind, counterpart in (("trade", "mark"), ("mark", "trade")):
        missing = set(maps[counterpart])-set(maps[kind])
        counts[kind] = len(missing)
        days = sorted({datetime.fromtimestamp(t/1000, UTC).strftime("%Y-%m-%d") for t in missing})
        for day in days:
            recovered = repair.fetch(symbol, kind, day)
            for stamp, row in recovered.items():
                if stamp in maps[kind]:
                    for key in ("close", "volume", "quote_volume"):
                        if key in row and not np.isclose(row[key], maps[kind][stamp][key], rtol=1e-12, atol=1e-12):
                            raise ValueError(f"Repair conflicts with source: {symbol}/{kind}/{day}/{stamp}")
                elif stamp in missing:
                    maps[kind][stamp] = row
                    if kind == "trade":
                        repaired_days.add(day)
            unresolved = sorted(t for t in missing if t not in maps[kind]
                and datetime.fromtimestamp(t/1000, UTC).strftime("%Y-%m-%d") == day)
            if unresolved:
                report = {"symbol": symbol, "kind": kind, "day": day,
                          "unresolved_open_ms": unresolved,
                          "unresolved_utc": [datetime.fromtimestamp(t/1000, UTC).isoformat() for t in unresolved]}
                write(audit_folder / f"{symbol}_{kind}_{day}_unresolved.json", report)
                raise ValueError(f"Unresolved repair: {symbol}/{kind}/{day}; "
                                 f"{len(unresolved)}hours; first={report['unresolved_utc'][0]}")
    return ([maps["trade"][t] for t in sorted(maps["trade"])],
            [maps["mark"][t] for t in sorted(maps["mark"])], repaired_days, counts)


def inherit_source_caches(base):
    """Copy input evidence/budgets only; leave the failed version and contract intact."""
    prior = base.parent / "v20261122_001"
    if prior.resolve() == base.resolve():
        return
    if any((prior / name).exists() for name in ("prepared/manifest.json", "results/run_contract.json")):
        raise ValueError("Failed version progressed beyond acquisition; explicit migration review required")
    for relative in ("repair/raw", "spot_benchmarks/raw"):
        source, target = prior / relative, base / relative
        if source.exists() and not target.exists():
            source.resolve().relative_to(base.parent.resolve())
            target.resolve().relative_to(base.resolve())
            shutil.copytree(source, target)
