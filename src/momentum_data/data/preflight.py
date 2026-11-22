"""Read-only complete held-proxy and cached-model verification."""

import bisect
import json
import pandas as pd
from ..settings import BASE, PREPARED, START, STOP, DAY, HOUR, YEARS, ms
from ..integrity import checked_manifest, write, verify_frozen_contract, sha
from ..models.annual import cached_predictions
from ..portfolio.ranking import portfolio_schedule
from .historical import ContinuousData


def make_schedule(predictions):
    result = {}
    for year in YEARS:
        sample = predictions[predictions.decision_date.str[:4] == str(year)]
        result.update(portfolio_schedule(sample, year, weeks=2, buffer=False)[0])
    return {d: w for d, w in result.items() if START <= ms(d) < STOP - DAY}


def audit_plan(data, plan, start=START, stop=STOP):
    """Check every required held proxy before any account simulation; accumulate all gaps."""
    changes = sorted((ms(d) + 2 * HOUR, w) for d, w in plan.items())
    times = [t for t, _ in changes]
    problems = []

    def issue(symbol, stamp, reason):
        problems.append({"symbol": symbol, "timestamp_ms": stamp, "reason": reason})

    def held(t):
        i = bisect.bisect_right(times, t) - 1
        return changes[i][1] if i >= 0 else {}

    for t in range(start, stop, DAY):
        for symbol in held(t):
            if data.mark(symbol, t) is None:
                issue(symbol, t, "held daily mark")
    for t, weights in changes:
        previous = held(t - 1)
        for symbol in set(previous) | set(weights):
            row = data.trades.get(symbol, {}).get(t - 2 * HOUR)
            if not row or row[0] <= 0:
                issue(symbol, t - HOUR, "known sizing close")
            if data.mark(symbol, t - HOUR) is None:
                issue(symbol, t - HOUR, "held/target decision mark")
            if data.vwap(symbol, t - HOUR) is None:
                issue(symbol, t, "execution VWAP")
    for symbol, entries in data.funding.items():
        for t, _ in entries:
            if start <= t <= stop - DAY and symbol in held(t - 1) and data.mark(symbol, t) is None:
                issue(symbol, t, "held funding mark")
    for symbol, end in data.terminal_ends.items():
        if start <= end < stop and symbol in held(end - 1):
            issue(symbol, end, "held terminal settlement unverified")
    final = stop - DAY - HOUR
    for symbol in held(final):
        if data.vwap(symbol, final - HOUR) is None:
            issue(symbol, final, "final liquidation VWAP")
    return {
        "success": not problems,
        "problem_count": len(problems),
        "problems": problems,
        "scheduled_rebalances": len(plan),
        "PnL_computed": False,
    }


def verify_inputs():
    verify_frozen_contract(BASE)
    checked_manifest(PREPARED)
    checked_manifest(BASE, "preflight_complete.json")
    frame, trades = [pd.read_parquet(PREPARED / (n + ".parquet")) for n in ("features", "trade")]
    forecasts, models = cached_predictions(frame, trades)
    plan = make_schedule(forecasts)
    if plan != json.loads((BASE / "schedule.json").read_text()):
        raise ValueError("Refactored ranking differs from frozen schedule")
    data = ContinuousData(PREPARED)
    audit = audit_plan(data, plan)
    if not audit["success"]:
        raise ValueError(f"Held proxy gaps: {audit['problems']}")
    events = data.events_range(START, STOP - DAY)
    return (
        data,
        events,
        plan,
        {
            "success": True,
            "scheduled_rebalances": len(plan),
            "events": len(events),
            "models": len(models),
            "new_model_fits": 0,
        },
    )
