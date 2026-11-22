"""Registered retrospective continuous reconstruction; no fitting or network access."""
import bisect
import csv
import io
import json
import zipfile
from datetime import UTC, datetime
from importlib.metadata import version

import lightgbm as lgb
import numpy as np
import pandas as pd
from acquire_usdm_universe import verify_payload
from audit_development_continuity import sha
from build_final_holdout_spot import benchmark, normalize_row
from final_holdout_common import (ROOT, PREPARED, DAY, HOUR, FEATURES, ms, write,
    bind, checked_manifest, matured_training)
from final_holdout_engine import FinalHistoricalData
from final_holdout_lifecycle import terminal_boundaries
from run_first_development import PARAMS
from strategy_adjustment_rules import portfolio_schedule

BASE = ROOT / "data/interim/continuous_reconstruction/v20261122_001"
REGISTRATION = ROOT / "experiments/016_continuous_2022_2026.md"
START, STOP = ms("2022-01-01"), ms("2026-11-01")
YEARS = tuple(range(2022, 2027))
MODEL_ROOTS = {
    2022: ROOT / "data/interim/first_development/v20261121_001/results_v003/model",
    2023: ROOT / "data/interim/validation_2023/v20261121_001/results/model",
    2024: ROOT / "data/interim/validation_2024/v20261121_002/results/model",
    2025: PREPARED.parent / "results/models/2025",
    2026: PREPARED.parent / "results/models/2026",
}
TRAINING_PREPARED = {y: MODEL_ROOTS[y].parents[1] / ("prepared_v003" if y == 2022 else "prepared") for y in (2022, 2023, 2024)}
SPOT_ROOTS = {
    2022: MODEL_ROOTS[2022].parents[1] / "spot_benchmarks",
    2023: MODEL_ROOTS[2023].parents[1] / "spot_benchmarks",
    2024: ROOT / "data/interim/validation_2024/v20261121_001/spot_benchmarks",
    2025: PREPARED.parent / "spot_benchmarks",
    2026: PREPARED.parent / "spot_benchmarks",
}


class ContinuousData(FinalHistoricalData):
    def events_range(self, start, last):
        if start < START or last >= STOP or start > last or start % DAY or last % DAY:
            raise ValueError("Event range exceeds continuous reconstruction")
        final = last-HOUR
        events = {}

        def add(symbol, stamp, kind, price, mark_at=None, rate=None):
            key = symbol, stamp
            if key in events:
                if rate is not None:
                    events[key]["rate"] = rate
                    events[key]["funding_price"] = price
                    events[key]["funding_mark_at"] = mark_at
                return
            events[key] = {"symbol": symbol, "stamp": stamp, "kind": kind,
                           "price": price, "mark_at": mark_at, "rate": rate,
                           "funding_price": price if rate is not None else None,
                           "funding_mark_at": mark_at if rate is not None else None}

        for day in range(start, last+1, DAY):
            for symbol in self.symbols:
                mark = self.mark(symbol, day)
                if mark:
                    add(symbol, day*1000000, "mark", *mark)
            anchor = self.mark("BTCUSDT", day)
            if not anchor:
                raise ValueError("Missing BTC snapshot anchor")
            add("BTCUSDT", day*1000000+100, "snapshot", anchor[0])
            if day < last and (datetime.fromtimestamp(day/1000, UTC).weekday() == 0 or day == start):
                for symbol in self.symbols:
                    mark = self.mark(symbol, day+HOUR)
                    if mark:
                        add(symbol, (day+HOUR)*1000000, "reference", *mark)
                for offset, kind in ((HOUR, "decision"), (2*HOUR, "check")):
                    anchor = self.mark("BTCUSDT", day+offset)
                    if not anchor:
                        raise ValueError("Missing BTC decision/check anchor")
                    add("BTCUSDT", (day+offset)*1000000+100, kind, anchor[0])
                for symbol in self.symbols:
                    price = self.vwap(symbol, day+HOUR)
                    if price:
                        add(symbol, (day+2*HOUR)*1000000, "execution", price)
        for symbol, end in getattr(self, "terminal_ends", {}).items():
            if symbol in self.symbols and start <= end <= last:
                prior = self.mark(symbol, end-1)
                add(symbol, end*1000000+50, "terminal_boundary", prior[0] if prior else 1.)
        for symbol in self.symbols:
            for stamp, rate in self.funding.get(symbol, []):
                if start <= stamp <= last:
                    mark = self.mark(symbol, stamp)
                    if mark:
                        add(symbol, stamp*1000000, "funding", *mark, rate=rate)
                    else:
                        add(symbol, stamp*1000000, "missing_funding_mark", 1., None, rate)
            price = self.vwap(symbol, final-HOUR)
            if price:
                add(symbol, final*1000000, "final", price)
        anchor = self.mark("BTCUSDT", final)
        if not anchor:
            raise ValueError("Missing BTC final anchor")
        add("BTCUSDT", final*1000000+100, "final_check", anchor[0])
        return [events[k] for k in sorted(events, key=lambda x: (x[1], x[0]))]


def contract():
    files = [REGISTRATION, PREPARED / "manifest.json", ROOT / "src/momentum_data/backtest_analysis.py"]
    # Freeze all transitive simulator/data-helper code, not just the new entry point.
    from final_holdout_common import CODE
    files += [ROOT / "scripts" / n for n in CODE]
    files += [ROOT / "scripts" / n for n in ("continuous_reconstruction.py", "run_continuous_reconstruction.py")]
    for folder in TRAINING_PREPARED.values():
        files += [folder / "manifest.json", folder / "features.parquet"]
    for folder in MODEL_ROOTS.values():
        files += [folder / n for n in ("model_summary.json", "training_samples.parquet", "lightgbm.txt", "shap_values.csv")]
        files += [folder / ("predictions.parquet" if "models" in folder.parts else "validation_predictions.parquet")]
    return {"hashes": {str(p.relative_to(ROOT)): sha(p) for p in files},
            "runtime": {n: version(n) for n in ("nautilus_trader", "pandas", "numpy", "lightgbm", "shap", "pyarrow")}}


def cached_predictions(features, trades):
    predictions, audits = [], []
    keys = ["decision_date", "instrument_id"]
    for year, folder in MODEL_ROOTS.items():
        meta = json.loads((folder / "model_summary.json").read_text())
        if "output_hashes" in meta:
            checked_manifest(folder, "model_summary.json")
        digest = meta.get("model_sha256", meta.get("frozen_model_sha256"))
        if digest and digest != sha(folder / "lightgbm.txt"):
            raise ValueError(f"Changed annual model: {year}")
        if meta["parameters"] != PARAMS or meta["features"] != FEATURES:
            raise ValueError(f"Changed model specification: {year}")
        cutoff = ms(f"{year}-01-01")
        train = pd.read_parquet(folder / "training_samples.parquet").sort_values(keys).reset_index(drop=True)
        if year <= 2024:
            source = TRAINING_PREPARED[year]
            original_meta = json.loads((source / "manifest.json").read_text())
            if sha(source / "features.parquet") != original_meta["output_hashes"]["features.parquet"]:
                raise ValueError("Original training feature source changed")
            original = pd.read_parquet(source / "features.parquet")
            expected_train = original[(original.feature_cutoff_ms < cutoff) &
                (original.label_available_ms < cutoff) & original.label.notna()].sort_values(keys).reset_index(drop=True)
        else:
            expected_train = matured_training(features, trades[trades.bar_open_ms < cutoff], cutoff)
        pd.testing.assert_frame_equal(train, expected_train[train.columns], check_exact=True, check_dtype=False)
        if not (train.label_available_ms < cutoff).all() or not (train.feature_cutoff_ms < cutoff).all():
            raise ValueError("Training label crosses forecast cutoff")
        name = "predictions.parquet" if year >= 2025 else "validation_predictions.parquet"
        sample = pd.read_parquet(folder / name).sort_values(keys).reset_index(drop=True)
        expected = features[(features.feature_cutoff_ms >= cutoff) &
                            (features.feature_cutoff_ms < min(ms(f"{year+1}-01-01"), STOP))].sort_values(keys).reset_index(drop=True)
        cols = keys + FEATURES + ["feature_cutoff_ms", "decision_ms", "label_available_ms"]
        pd.testing.assert_frame_equal(sample[cols], expected[cols], check_exact=True, check_dtype=False)
        if sample.duplicated(keys).any() or sample.empty:
            raise ValueError("Missing/duplicate annual forecast rows")
        booster = lgb.Booster(model_file=str(folder / "lightgbm.txt"))
        if not np.allclose(booster.predict(sample[FEATURES]), sample.score, atol=1e-12, rtol=0):
            raise ValueError("Cached model prediction mismatch")
        attribution = pd.read_csv(folder / "shap_values.csv").sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(attribution[keys], sample[keys], check_dtype=False)
        shap_columns = ["shap_"+f for f in FEATURES]
        error = np.max(np.abs(attribution[shap_columns].sum(axis=1)+attribution.expected_value-sample.score))
        if not np.isfinite(error) or error > 1e-6:
            raise ValueError("Cached SHAP additivity mismatch")
        # Labels in old development caches are irrelevant to forecasting: never carry them into plans.
        predictions.append(sample[cols+["score"]])
        audits.append({"year": year, "training_rows": len(train), "forecast_rows": len(sample),
                       "cutoff_ms": cutoff, "latest_label_available_ms": int(train.label_available_ms.max()),
                       "model_sha256": sha(folder / "lightgbm.txt"), "shap_additivity_max_error": float(error)})
    return pd.concat(predictions, ignore_index=True), audits


def make_schedule(predictions):
    result = {}
    for year in YEARS:
        sample = predictions[predictions.decision_date.str[:4] == str(year)]
        result.update(portfolio_schedule(sample, year, weeks=2, buffer=False)[0])
    return {d: w for d, w in result.items() if START <= ms(d) < STOP-DAY}


def audit_plan(data, plan, start=START, stop=STOP):
    """Check every required held proxy before any account simulation; accumulate all gaps."""
    changes = sorted((ms(d)+2*HOUR, w) for d, w in plan.items())
    times = [t for t, _ in changes]
    problems = []
    def issue(symbol, stamp, reason):
        problems.append({"symbol": symbol, "timestamp_ms": stamp, "reason": reason})
    def held(t):
        i = bisect.bisect_right(times, t)-1
        return changes[i][1] if i >= 0 else {}
    for t in range(start, stop, DAY):
        for symbol in held(t):
            if data.mark(symbol, t) is None:
                issue(symbol, t, "held daily mark")
    for t, weights in changes:
        previous = held(t-1)
        for symbol in set(previous) | set(weights):
            row = data.trades.get(symbol, {}).get(t-2*HOUR)
            if not row or row[0] <= 0:
                issue(symbol, t-HOUR, "known sizing close")
            if data.mark(symbol, t-HOUR) is None:
                issue(symbol, t-HOUR, "held/target decision mark")
            if data.vwap(symbol, t-HOUR) is None:
                issue(symbol, t, "execution VWAP")
    for symbol, entries in data.funding.items():
        for t, _ in entries:
            if start <= t <= stop-DAY and symbol in held(t-1) and data.mark(symbol, t) is None:
                issue(symbol, t, "held funding mark")
    for symbol, end in data.terminal_ends.items():
        if start <= end < stop and symbol in held(end-1):
            issue(symbol, end, "held terminal settlement unverified")
    final = stop-DAY-HOUR
    for symbol in held(final):
        if data.vwap(symbol, final-HOUR) is None:
            issue(symbol, final, "final liquidation VWAP")
    return {"success": not problems, "problem_count": len(problems), "problems": problems,
            "scheduled_rebalances": len(plan), "PnL_computed": False}


def build_spot():
    sources, ledgers = [], {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        observed = {}
        for year in YEARS:
            for month in range(1, 11 if year == 2026 else 13):
                label = f"{year}-{month:02d}"
                folder = SPOT_ROOTS[year] / "raw" / symbol / label
                filename = f"{symbol}-1h-{label}.zip"
                body = (folder / "archive.zip").read_bytes()
                digest = verify_payload(body, (folder / "checksum.txt").read_bytes(), filename, len(body))
                if digest != json.loads((folder / "source.json").read_text())["sha256"]:
                    raise ValueError("Spot source metadata mismatch")
                with zipfile.ZipFile(io.BytesIO(body)) as z:
                    if z.namelist() != [filename[:-4]+".csv"]:
                        raise ValueError("Unexpected spot archive member")
                    for raw in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8-sig"))):
                        if not raw or raw[0] == "open_time":
                            continue
                        row, _ = normalize_row(raw)
                        t = int(row[0])
                        if t <= int(row[6]) < t+HOUR-1:
                            continue
                        if t in observed or t % HOUR:
                            raise ValueError("Duplicate/off-grid spot hour")
                        observed[t] = {"close": float(row[4]), "volume": float(row[5]), "quote": float(row[7])}
                sources.append({"path": str(folder.relative_to(ROOT)), "sha256": digest})
        required = {START+HOUR, STOP-DAY-2*HOUR} | set(range(START+DAY-HOUR, STOP-DAY, DAY))
        if not required.issubset(observed) or any(observed[t]["close"] <= 0 for t in required):
            raise ValueError("Incomplete spot benchmark calendar")
        nav, ledger = benchmark(observed, START, STOP)
        nav.to_csv(BASE / f"{symbol}_spot.csv", index=False)
        ledgers[symbol] = ledger
    write(BASE / "spot_ledger.json", {"source_archives": len(sources), "sources": sources, "ledgers": ledgers,
        "buy_timestamp_UTC": "2022-01-01T02:00:00Z", "sell_timestamp_UTC": "2026-10-30T23:00:00Z",
        "fee_bps_per_side": 10, "slippage_bps_per_side": 5, "annual_resets": 0})


def preflight():
    BASE.mkdir(parents=True, exist_ok=True)
    bind(BASE / "contract.json", contract())
    meta = checked_manifest(PREPARED)
    boundaries = terminal_boundaries(meta["symbols"])
    if boundaries != meta.get("terminal_boundaries", {}):
        raise ValueError("Prepared terminal evidence mismatch")
    frame, trades = [pd.read_parquet(PREPARED / (n+".parquet")) for n in ("features", "trade")]
    forecasts, models = cached_predictions(frame, trades)
    plan = make_schedule(forecasts)
    data = ContinuousData(PREPARED)
    audit = audit_plan(data, plan)
    # Build the entire event grid as a source/anchor/collision check, without PnL.
    events = data.events_range(START, STOP-DAY)
    audit.update({"event_count": len(events), "models": models, "new_model_fits": 0,
                  "prepared_manifest_sha256": sha(PREPARED / "manifest.json")})
    write(BASE / "preflight.json", audit)
    if not audit["success"]:
        raise ValueError(f"Preflight found {audit['problem_count']} unresolved proxies; see {BASE / 'preflight.json'}")
    build_spot()
    forecasts.to_parquet(BASE / "forecasts.parquet", index=False)
    write(BASE / "schedule.json", plan)
    products = ["preflight.json", "forecasts.parquet", "schedule.json", "BTCUSDT_spot.csv", "ETHUSDT_spot.csv", "spot_ledger.json"]
    write(BASE / "preflight_complete.json", {"success": True, "contract_sha256": sha(BASE / "contract.json"),
        "output_hashes": {n: sha(BASE / n) for n in products}})
    print(json.dumps({k: v for k, v in audit.items() if k not in ("models", "problems")}), flush=True)
    return data, events, plan
