"""Frozen final-holdout rules and integrity helpers; importing loads no market data."""
import json
import math
from datetime import date, timedelta
from importlib.metadata import version

import numpy as np
import pandas as pd
from audit_development_continuity import sha
from development_continuity_rules import normalized, numeric_history
from prepare_first_development import DAY, FEATURES, HOUR, ROOT, funding_feature
from strategy_adjustment_rules import portfolio_schedule

BASE = ROOT / "data/interim/final_holdout/v20261122_003"
OLD = ROOT / "data/interim/validation_2024/v20261121_002/prepared"
PREPARED = BASE / "prepared"
REGISTRATION = "experiments/015_final_holdout_2025_2026.md"
CODE = ["final_holdout_common.py", "final_holdout_engine.py", "final_holdout_migration.py", "final_holdout_lifecycle.py", "prepare_final_holdout.py",
        "build_final_holdout_spot.py", "run_final_holdout_cases.py", "report_final_holdout.py",
        "final_holdout_acquisition.py", "run_final_holdout.py", "first_development_engine.py", "run_first_development.py",
        "prepare_first_development.py", "prepare_validation_2024.py", "strategy_adjustment_rules.py",
        "development_continuity_rules.py", "audit_development_continuity.py",
        "reconcile_mark_gaps.py", "recover_development_marks.py", "acquire_usdm_universe.py",
        "check_universe_feasibility.py", "check_lifecycle_rows.py", "review_usdm_lifecycle.py"]


def ms(value):
    return int(pd.Timestamp(value, tz="UTC").timestamp()*1000)


START, STOP = ms("2025-01-01"), ms("2026-11-01")
WINDOWS = {"2025": (START, ms("2026-01-01")),
           "2026_partial": (ms("2026-01-01"), STOP), "continuous": (START, STOP)}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(v) for v in value]
        if isinstance(value, np.generic):
            value = value.item()
        return None if isinstance(value, float) and not math.isfinite(value) else value
    path.write_text(json.dumps(clean(obj), indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")


def bind(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f"Immutable contract mismatch: {path}; do not delete contracts")
    else:
        write(path, value)


def code_contract():
    return {"registration_sha256": sha(ROOT / REGISTRATION),
            "lifecycle_events_sha256": sha(ROOT / "data/interim/usdm_universe/lifecycle_review_20261118/events.json"),
            "old_prepared_sha256": sha(OLD / "manifest.json"),
            "code_hashes": {f"scripts/{p}": sha(ROOT / "scripts" / p) for p in CODE},
            "analysis_sha256": sha(ROOT / "src/momentum_data/backtest_analysis.py"),
            "runtime": {p: version(p) for p in ("nautilus_trader", "lightgbm", "shap", "numpy", "pandas", "pyarrow")}}


def checked_manifest(folder, filename="manifest.json"):
    obj = json.loads((folder / filename).read_text())
    if any(sha(folder / n) != h for n, h in obj["output_hashes"].items()):
        raise ValueError(f"Changed outputs in {folder}")
    return obj


def months():
    return [f"{y}-{m:02d}" for y in (2025, 2026) for m in range(1, 13 if y == 2025 else 11)]


def mondays(year):
    day = date(year, 1, 1)
    day += timedelta(days=(7-day.weekday()) % 7)
    out = []
    while day.year == year and day < date(2026, 11, 1):
        out.append(day)
        day += timedelta(days=7)
    return out


def features_for_dates(rows, marks, funding, symbol, dates):
    points = [normalized(r) for r in rows]
    history = numeric_history(points)
    normalized_days = {p["day"]: p for p in points}
    by_day = {date.fromisoformat(r["data_day"]): r for r in rows}
    counts = pd.Series([r["bar_open_ms"]//DAY for r in marks], dtype="int64").value_counts().to_dict()
    result = []
    for decision in dates:
        cutoff, day = ms(decision.isoformat()), decision-timedelta(days=1)
        row = by_day.get(day)
        recent = [by_day.get(day-timedelta(days=i)) for i in range(7)]
        valid = all(recent) and all(normalized_days[day-timedelta(days=i)]["imbalance"] for i in range(7))
        rate = funding_feature(funding, cutoff)
        if not (row and history[day] >= 121 and counts.get((cutoff-DAY)//DAY, 0) == 24
                and valid and (row["base_failure_mask"] & ~(8 | 2)) == 0 and rate is not None):
            continue
        # Match original compensated summation exactly.
        quote = math.fsum(r["trade_quote_volume_sum"] for r in recent)
        buy = math.fsum(r["taker_buy_quote_volume_sum"] for r in recent)
        if quote <= 0:
            continue
        item = {"instrument_id": symbol, "decision_date": decision.isoformat(),
                "feature_cutoff_ms": cutoff, "decision_ms": cutoff+HOUR,
                "label_available_ms": cutoff+3*HOUR+7*DAY, "label": None,
                "funding7": rate, "imbalance7": 2*buy/quote-1}
        for horizon in (20, 60, 120):
            item[f"momentum{horizon}"] = row["trade_close"]/by_day[day-timedelta(days=horizon)]["trade_close"]-1
        if not all(np.isfinite(item[k]) for k in FEATURES):
            raise ValueError("Nonfinite feature")
        result.append(item)
    return result


def matured_training(features, trades, cutoff):
    frame = features[(features.feature_cutoff_ms < cutoff) & (features.label_available_ms < cutoff)].copy()
    frame = frame.sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    past = trades[trades.bar_open_ms < cutoff]
    lookup = {(r.instrument_id, int(r.bar_open_ms)): r for r in past.itertuples()}
    for row in frame.itertuples():
        if pd.notna(row.label):
            continue
        entry = int(row.feature_cutoff_ms)+HOUR
        exit_time = entry+7*DAY
        if exit_time+2*HOUR != row.label_available_ms or exit_time+2*HOUR >= cutoff:
            raise ValueError("Invalid label timing")
        a, b = lookup.get((row.instrument_id, entry)), lookup.get((row.instrument_id, exit_time))
        if a is not None and b is not None and a.volume > 0 and b.volume > 0:
            frame.loc[row.Index, "label"] = (b.quote_volume/b.volume)/(a.quote_volume/a.volume)-1
    frame = frame[frame.label.notna()].reset_index(drop=True)
    if not np.isfinite(frame[FEATURES+["label"]].to_numpy(float)).all():
        raise ValueError("Invalid matured training values")
    return frame


def schedules(predictions, score="score"):
    out = {}
    for y in (2025, 2026):
        sample = predictions[predictions.feature_cutoff_ms.between(ms(f"{y}-01-01"),
                    min(ms(f"{y+1}-01-01"), STOP)-1)].copy()
        sample["score"] = sample[score]
        plan = portfolio_schedule(sample, y, weeks=2, buffer=False)[0]
        out.update({d: w for d, w in plan.items() if START <= ms(d) < STOP})
    return out


def window_schedule(plan, name):
    a, b = WINDOWS[name]
    return {d: w for d, w in plan.items() if a <= ms(d) < b}
