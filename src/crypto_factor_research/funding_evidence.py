"""Audit saved funding-break brackets against public observations; never fill rates."""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

import pyarrow.parquet as pq

from .config import DAY, HOUR, load_json, sha
from .repair import write_json
from .window_data import PublicSources


def compare_records(symbol, before, after, rows):
    if not isinstance(rows, list) or len(rows) >= 1000:
        raise ValueError("Funding API response invalid or possibly truncated")
    observed = {}
    for row in rows:
        t, rate = int(row["fundingTime"]), float(row["fundingRate"])
        if row["symbol"] != symbol or not math.isfinite(rate):
            raise ValueError("Funding API identity/rate invalid")
        if not before[0] - HOUR <= t <= after[0] + HOUR or t in observed:
            raise ValueError("Funding API timestamp duplicate/outside requested range")
        observed[t] = rate
    # Millisecond publication jitter is tolerated only for comparing anchors;
    # no timestamps or rates are written into strategy inputs.
    for t, rate in [before, after]:
        anchors = [(s, v) for s, v in observed.items() if abs(s - t) <= 1000]
        if len(anchors) != 1 or abs(anchors[0][1] - rate) > 1e-12:
            return {"status": "api_anchors_disagree", "api_rows": len(rows)}
    interior = sorted(t for t in observed if before[0] + 1000 < t < after[0] - 1000)
    return {
        "status": "api_has_additional_events" if interior else "api_has_same_observed_gap",
        "api_rows": len(rows),
        "interior_event_times_ms": interior,
    }


def audit_breaks(root, run_dir, limit=None, client=None):
    root, run = Path(root).resolve(), Path(run_dir)
    run = (root / run).resolve() if not run.is_absolute() else run.resolve()
    run.relative_to(root)
    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive")
    problems = load_json(run / "preflight_problems.json")
    targets = sorted(
        {
            (p["symbol"], int(p["timestamp_ms"]))
            for p in problems
            if p.get("reason") == "unresolved_observed_schedule_break"
        }
    )
    all_targets = len(targets)
    targets = targets[:limit] if limit is not None else targets
    prepared = load_json(run / "manifest.json")
    funding = run / "funding.parquet"
    funding_hash = sha(funding)
    if funding_hash != prepared["output_hashes"]["funding.parquet"]:
        raise ValueError("Prepared funding source changed")
    ident = {
        "run_dir": str(run),
        "problems_sha256": sha(run / "preflight_problems.json"),
        "funding_sha256": funding_hash,
        "code_sha256": sha(Path(__file__)),
        "limit": limit,
    }
    key = hashlib.sha256(json.dumps(ident, sort_keys=True).encode()).hexdigest()[:20]
    output = root / "reports/tables/funding_breaks" / key
    output.mkdir(parents=True, exist_ok=True)
    print("Funding evidence output: " + str(output), flush=True)
    client = client or PublicSources(
        root / "data/repairs/first_window_public", budget=all_targets + 5
    )
    groups = {}
    if targets:
        frame = pq.read_table(
            funding,
            columns=["instrument_id", "event_timestamp_ms", "funding_rate"],
            filters=[
                ("instrument_id", "in", sorted({s for s, _ in targets})),
                ("event_timestamp_ms", ">=", min(t for _, t in targets) - DAY),
                ("event_timestamp_ms", "<=", max(t for _, t in targets) + 2 * DAY),
            ],
        ).to_pandas()
        groups = {
            s: g.sort_values("event_timestamp_ms")
            for s, g in frame.groupby("instrument_id", observed=True)
        }
    results = []
    for i, (symbol, timestamp) in enumerate(targets):
        result = {"symbol": symbol, "before_ms": timestamp}
        try:
            group = groups[symbol]
            before_rows = group[group.event_timestamp_ms.eq(timestamp)]
            after_rows = group[group.event_timestamp_ms.gt(timestamp)]
            if len(before_rows) != 1 or after_rows.empty:
                raise ValueError("Cannot bound the saved funding break")
            a, b = before_rows.iloc[0], after_rows.iloc[0]
            before = (int(a.event_timestamp_ms), float(a.funding_rate))
            after = (int(b.event_timestamp_ms), float(b.funding_rate))
            url = "https://fapi.binance.com/fapi/v1/fundingRate?" + urlencode(
                {
                    "symbol": symbol,
                    "startTime": before[0] - HOUR,
                    "endTime": after[0] + HOUR,
                    "limit": 1000,
                }
            )
            body, source = client.get(url)
            result.update(compare_records(symbol, before, after, json.loads(body)))
            result.update(after_ms=after[0], source=source, url=url)
        except Exception as exc:
            result.update(status="request_or_validation_failed", error=str(exc))
        results.append(result)
        write_json(output / "evidence.json", {"identity": ident, "records": results})
        if (i + 1) % 10 == 0 or i + 1 == len(targets):
            print(f"Funding evidence {i + 1}/{len(targets)}", flush=True)
    counts = dict(Counter(row["status"] for row in results))
    summary = {
        "success": not counts.get("request_or_validation_failed", 0),
        "meaning": "Evidence collection only; absence is not proof of zero funding",
        "unique_saved_breaks": all_targets,
        "checked_breaks": len(results),
        "full_scope": len(targets) == all_targets,
        "status_counts": counts,
        "PnL_computed": False,
        "strategy_records_modified": 0,
        "financial_execution_ready": False,
        "evidence_path": str(output / "evidence.json"),
    }
    write_json(output / "summary.json", summary)
    print(json.dumps(summary), flush=True)
    return summary
