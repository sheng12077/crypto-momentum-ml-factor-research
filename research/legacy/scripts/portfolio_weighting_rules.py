"""Experiment012 fixed-membership allocation; risk inputs must precede decisions."""

import numpy as np
import pandas as pd
from strategy_adjustment_rules import mondays

DAY = 86_400_000
HOUR = 3_600_000
SCHEMES = ("EQ", "IV60", "RANK")
SIGMA_FLOOR = .005
CAP = .15
SIDE_BUDGET = .5
RANK_SHARES = np.array([.25, .225, .20, .175, .15])


def capped_weights(raw, budget=SIDE_BUDGET, cap=CAP):
    raw = np.asarray(raw, dtype=float)
    if not len(raw) or not np.isfinite(raw).all() or (raw <= 0).any() or len(raw)*cap < budget:
        raise ValueError("Invalid or infeasible capped allocation")
    weights = np.zeros(len(raw))
    free = np.ones(len(raw), dtype=bool)
    for _ in range(len(raw)+1):
        indices = np.flatnonzero(free)
        remaining = budget-weights.sum()
        if not len(indices):
            break
        proposed = remaining*raw[indices]/raw[indices].sum()
        over = proposed > cap+1e-14
        if not over.any():
            weights[indices] = proposed
            break
        clipped = indices[over]
        weights[clipped] = cap
        free[clipped] = False
    if abs(weights.sum()-budget) > 1e-12 or (weights > cap+1e-12).any():
        raise ValueError("Capped redistribution failed")
    return weights


class DailyRisk:
    def __init__(self, hourly):
        if (hourly.bar_open_ms >= 1704067200000).any():
            raise ValueError("Risk source exceeds2023scope")
        daily = hourly[(hourly.bar_open_ms % DAY == 23*HOUR)
                       & (hourly.bar_open_ms+HOUR < 1704067200000)].copy()
        if daily.duplicated(["instrument_id", "bar_open_ms"]).any():
            raise ValueError("Duplicate daily closing observation")
        self.series = {}
        for symbol, group in daily.groupby("instrument_id"):
            group = group.sort_values("bar_open_ms")
            self.series[symbol] = (group.bar_open_ms.to_numpy(np.int64)+HOUR, group.close.to_numpy(float))
        self.cache = {}

    def estimate(self, symbol, cutoff):
        key = symbol, int(cutoff)
        if key in self.cache:
            return self.cache[key]
        times, values = self.series[symbol]
        stop = int(np.searchsorted(times, cutoff, side="right"))
        stamps, prices = times[max(0, stop-61):stop], values[max(0, stop-61):stop]
        if len(stamps) != 61 or stamps[-1] != cutoff or not (np.diff(stamps) == DAY).all():
            raise ValueError(f"Need61consecutive closes known by cutoff:{symbol}/{cutoff}")
        if not np.isfinite(prices).all() or (prices <= 0).any():
            raise ValueError("Invalid risk prices")
        returns = prices[1:]/prices[:-1]-1
        sigma = float(returns.std(ddof=1))
        result = {"sigma_daily_raw": sigma, "sigma_daily_used": max(SIGMA_FLOOR, sigma),
                  "risk_first_available_ms": int(stamps[0]), "risk_last_available_ms": int(stamps[-1]),
                  "risk_prices": 61}
        self.cache[key] = result
        return result


def build_schedule(sample, year, scheme, risk):
    if scheme not in SCHEMES:
        raise ValueError("Unregistered weighting scheme")
    if sample.duplicated(["decision_date", "instrument_id"]).any():
        raise ValueError("Duplicate feature key")
    weights, audit = {}, []
    for day in mondays(year)[::2]:
        rows = sample[sample.decision_date == day].sort_values(
            ["score", "instrument_id"], ascending=[False, True], kind="stable")
        weights[day] = {}
        if len(rows) < 20:
            continue
        cutoff = int(pd.Timestamp(day, tz="UTC").timestamp()*1000)
        sides = (("long", 1, rows.iloc[:5]), ("short", -1, rows.iloc[-5:].iloc[::-1]))
        for side, sign, group in sides:
            estimates = [risk.estimate(symbol, cutoff) for symbol in group.instrument_id]
            if scheme == "EQ":
                absolute = np.full(5, .1)
            elif scheme == "RANK":
                absolute = SIDE_BUDGET*RANK_SHARES
            else:
                absolute = capped_weights([1/r["sigma_daily_used"] for r in estimates])
            effective = float(1/np.square(absolute/SIDE_BUDGET).sum())
            for rank, (row, amount, estimate) in enumerate(zip(group.itertuples(), absolute, estimates, strict=True), 1):
                weights[day][row.instrument_id] = sign*float(amount)
                audit.append({"year": year, "scheme": scheme, "decision_date": day,
                              "instrument_id": row.instrument_id, "side": side, "rank_within_side": rank,
                              "model_score": float(row.score), "weight": sign*float(amount),
                              "effective_names_side": effective, "cap_active": bool(amount >= CAP-1e-12), **estimate})
        values = np.array(list(weights[day].values()))
        if len(values) != 10 or abs(values.sum()) > 1e-12 or abs(abs(values).sum()-1) > 1e-12:
            raise ValueError("Side budgets or membership failed")
    return weights, audit
