"""Experiment020 staged CLI:prepare,fit,complete preflight,Nautilus cases,report."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DAY, HOUR, load_json, sha
from .repair import write_json
from .window_data import (
    MARKET_COLUMNS,
    PublicSources,
    WindowData,
    episode_notice,
    ms,
    read_market,
    window_label,
)


def identity(root, config_path, config):
    import lightgbm
    import nautilus_trader

    from momentum_data.backtest import engine

    files = [
        Path(__file__),
        Path(__file__).with_name("window_data.py"),
        Path(__file__).with_name("repair.py"),
        Path(engine.__file__),
    ]
    return {
        "config_sha256": sha(config_path),
        "code": {str(p.relative_to(root)): sha(p) for p in files},
        "capacity_summary_sha256": sha(root / config["capacity_run"] / "summary.json"),
        "repair_assessment_sha256": sha(root / config["repair_run"] / "assessment.json"),
        "registration_sha256": sha(
            root / config.get("registration", "experiments/020_dynamic_first_window.md")
        ),
        "runtime": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "lightgbm": lightgbm.__version__,
            "nautilus_trader": nautilus_trader.__version__,
        },
    }


def checked(path, name="manifest.json"):
    meta = load_json(path / name)
    for field in ["output_hashes", "source_bindings"]:
        for key, expected in meta.get(field, {}).items():
            source = path / key if field == "output_hashes" else Path(key)
            if sha(source) != expected:
                raise ValueError("Bound first-window artifact changed:" + str(source))
    return meta


def prepare(root, config, path, ident):
    if (path / "manifest.json").exists():
        meta = checked(path)
        if meta["identity"] != ident:
            raise ValueError("First-window configuration changed")
        return meta
    path.mkdir(parents=True, exist_ok=True)
    capacity = root / config["capacity_run"]
    meta = checked(capacity, "summary.json")
    frame = pd.read_parquet(capacity / "dated_candidates.parquet")
    frame = frame[
        frame.feature_cutoff_ms.ge(ms(config["train_start"]))
        & frame.feature_cutoff_ms.lt(ms(config["stop_exclusive"]))
        & frame.provisional_entry_candidate
    ].copy()
    client = PublicSources(root / config["public_cache"])
    notices, errors = {}, []
    metadata_record = load_json(root / config["repair_run"] / "evidence/exchange_info/source.json")
    if sha(metadata_record["path"]) != metadata_record["sha256"]:
        raise ValueError("Episode metadata changed")
    metadata = {x["symbol"]: x for x in load_json(metadata_record["path"])["symbols"]}
    client.bindings[metadata_record["path"]] = metadata_record["sha256"]
    for item in config["cessation_notices"]:
        try:
            notice = client.notice(item)
            row, source = client.bar(item["symbol"], "trade", notice["exit_bar_ms"], "1m")
            if row["volume"] <= 0 or row["quote_volume"] <= 0:
                raise ValueError("Risk exit has zero traded volume")
            notice.update(exit_vwap=row["quote_volume"] / row["volume"], exit_source=source)
            relaunch = metadata.get(item["symbol"], {}).get("onboardDate", 0)
            if "relaunch_article_code" in item:
                relaunch, relaunch_source = client.relaunch(item)
                if relaunch <= notice["effective_ms"]:
                    raise ValueError("Relaunch must follow cessation")
                notice["relaunch_source"] = relaunch_source
            if relaunch > notice["effective_ms"]:
                notice["valid_to_ms"] = int(relaunch)
            key = item["symbol"]
            if key in notices:
                key += "@" + item["effective_utc"]
            if key in notices:
                raise ValueError("Duplicate cessation assertion:" + key)
            notices[key] = notice
        except Exception as exc:
            errors.append(
                {"symbol": item["symbol"], "issue": "notice_or_exit_bar", "error": str(exc)}
            )
    for symbol in {n["symbol"] for n in notices.values()}:
        episodes = sorted(
            [n for n in notices.values() if n["symbol"] == symbol],
            key=lambda n: n["effective_ms"],
        )
        for earlier, later in zip(episodes, episodes[1:], strict=False):
            if earlier.get("valid_to_ms", 2**63 - 1) > later["blocked_from_ms"]:
                errors.append({"symbol": symbol, "issue": "overlapping_cessation_episodes"})
    write_json(path / "source_errors.json", errors)
    if errors:
        raise ValueError("All notice/exit errors saved to source_errors.json")
    frame = frame[
        frame.apply(
            lambda row: (
                episode_notice(notices, row.instrument_id, row.decision_ms) is None
                or row.decision_ms
                < episode_notice(notices, row.instrument_id, row.decision_ms)["blocked_from_ms"]
            ),
            axis=1,
        )
    ].copy()
    frame = frame.drop(
        columns=[name for name in frame.columns if name.startswith("known_funding_breaks_next_")]
    )
    frame["decision_date"] = pd.to_datetime(
        frame.feature_cutoff_ms, unit="ms", utc=True
    ).dt.strftime("%Y-%m-%d")
    symbols = set(frame.instrument_id) | {"BTCUSDT", "ETHUSDT"}
    print(
        json.dumps({"stage": "prepare", "symbols": len(symbols), "candidate_rows": len(frame)}),
        flush=True,
    )
    market, bindings = read_market(root, config, symbols)
    for kind, value in market.items():
        value.to_parquet(path / (kind + ".parquet"), index=False)
    frame.to_parquet(path / "features.parquet", index=False)
    write_json(path / "notices.json", notices)
    bindings.update(client.bindings)
    bindings[str(capacity / "dated_candidates.parquet")] = meta["output_hashes"][
        "dated_candidates.parquet"
    ]
    result = {
        "success": True,
        "identity": ident,
        "symbols": sorted(symbols),
        "candidate_rows": len(frame),
        "market_rows": {kind: len(value) for kind, value in market.items()},
        "source_bindings": bindings,
        "output_hashes": {
            name: sha(path / name)
            for name in [
                "features.parquet",
                "trade.parquet",
                "mark.parquet",
                "funding.parquet",
                "notices.json",
                "source_errors.json",
            ]
        },
        "PnL_computed": False,
        "execution_ready": False,
    }
    write_json(path / "manifest.json", result)
    return result


def load_data(path):
    market = {
        kind: pd.read_parquet(path / (kind + ".parquet"), columns=columns)
        for kind, columns in MARKET_COLUMNS.items()
    }
    data = WindowData(market, load_json(path / "notices.json"))
    for symbol, notice in data.notices.items():
        data.exit_prices[symbol] = notice["exit_vwap"]
    recovery = path / "recovered_bars.jsonl"
    if recovery.exists():
        for line in recovery.read_text().splitlines():
            item = json.loads(line)
            if sha(item["source"]["path"]) != item["source"]["sha256"]:
                raise ValueError("Recovered preflight bar changed")
            data.add_bar(item["symbol"], item["kind"], item["row"])
    return data


def training_rows(frame, data, cutoff):
    samples = frame[frame.feature_cutoff_ms.lt(cutoff)].copy()
    samples["label_available_ms"] = samples.feature_cutoff_ms + 7 * DAY + 3 * HOUR
    samples = samples[samples.label_available_ms.lt(cutoff)].copy()
    accepted, rejected = [], []
    for row in samples.to_dict("records"):
        entry = row["feature_cutoff_ms"] + HOUR
        end = entry + 7 * DAY
        notice = episode_notice(data.notices, row["instrument_id"], entry)
        a, b = data.vwap(row["instrument_id"], entry), data.vwap(row["instrument_id"], end)
        if not a or not b or (notice and end + HOUR >= notice["effective_ms"]):
            rejected.append(
                {
                    "instrument_id": row["instrument_id"],
                    "feature_cutoff_ms": row["feature_cutoff_ms"],
                    "reason": "label_price_or_cessation_boundary",
                }
            )
            continue
        row["label"] = b / a - 1
        accepted.append(row)
    train = (
        pd.DataFrame(accepted)
        .sort_values(["feature_cutoff_ms", "instrument_id"])
        .reset_index(drop=True)
    )
    return train, rejected


def ranked_schedule(frame, year, weeks=2, minimum=20, stop_exclusive=None):
    mondays = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="W-MON", tz="UTC")[::weeks]
    if stop_exclusive is not None:
        # Execution completes at decision + 2h; the final close is last NAV - 1h.
        final_close = ms(stop_exclusive) - DAY - HOUR
        mondays = [day for day in mondays if day.value // 1000000 + 2 * HOUR < final_close]
    schedule = {}
    for day in mondays:
        sample = frame[frame.feature_cutoff_ms.eq(int(day.timestamp() * 1000))].sort_values(
            ["score", "instrument_id"], ascending=[False, True], kind="stable"
        )
        names = sample.instrument_id.tolist()
        schedule[day.strftime("%Y-%m-%d")] = (
            {**dict.fromkeys(names[:5], 0.1), **dict.fromkeys(names[-5:], -0.1)}
            if len(names) >= minimum
            else {}
        )
    return schedule


def score_control(frame, kind, seed=None):
    result = frame.copy()
    if kind == "momentum60":
        result["score"] = result.momentum60
    elif kind == "equal_groups":
        groups = result.groupby("feature_cutoff_ms")
        ranks = groups[["momentum20", "momentum60", "momentum120", "funding7", "imbalance7"]].rank(
            pct=True
        )
        result["score"] = (
            ranks[["momentum20", "momentum60", "momentum120"]].mean(axis=1)
            + (1 - ranks.funding7)
            + ranks.imbalance7
        ) / 3
    elif kind == "random":
        result["score"] = [
            int.from_bytes(hashlib.sha256(f"{seed}|{t}|{s}".encode()).digest()[:8], "big") / 2**64
            for t, s in zip(result.feature_cutoff_ms, result.instrument_id, strict=True)
        ]
    else:
        raise ValueError("Unknown fixed control")
    return result


def fit(root, config, path, data):
    import lightgbm as lgb

    if (path / "model/summary.json").exists():
        return checked(path / "model", "summary.json")
    frame = pd.read_parquet(path / "features.parquet")
    cutoff = ms(config["train_stop"])
    train, rejected = training_rows(frame, data, cutoff)
    if len(train) < 100 or not train.label_available_ms.lt(cutoff).all():
        raise ValueError("Invalid/insufficient matured training data")
    test = frame[frame.feature_cutoff_ms.ge(cutoff)].copy().reset_index(drop=True)
    features = config["features"]
    model = lgb.LGBMRegressor(**config["model_parameters"])
    model.fit(train[features], train.label)
    test["score"] = model.predict(test[features])
    contribution = model.booster_.predict(test[features], pred_contrib=True, num_threads=1)
    error = float(np.max(np.abs(contribution.sum(axis=1) - test.score.to_numpy())))
    if not np.isfinite(error) or error > 1e-6:
        raise ValueError("TreeSHAP additivity failed")
    out = path / "model"
    out.mkdir(exist_ok=True)
    model.booster_.save_model(str(out / "lightgbm.txt"))
    train.to_parquet(out / "training_rows.parquet", index=False)
    test.to_parquet(out / "predictions.parquet", index=False)
    shap = test[["instrument_id", "feature_cutoff_ms"]].copy()
    for i, name in enumerate(features):
        shap["shap_" + name] = contribution[:, i]
    shap["expected_value"] = contribution[:, -1]
    shap.to_parquet(out / "shap_values.parquet", index=False)
    pd.DataFrame(
        {"feature": features, "mean_absolute_shap": np.abs(contribution[:, :-1]).mean(axis=0)}
    ).to_csv(out / "shap_importance.csv", index=False)
    group_values = {
        "momentum": contribution[:, :3].sum(axis=1),
        "funding": contribution[:, 3],
        "imbalance": contribution[:, 4],
    }
    pd.DataFrame(
        {
            "factor_group": list(group_values),
            "mean_absolute_group_shap": [float(np.abs(x).mean()) for x in group_values.values()],
        }
    ).to_csv(out / "shap_group_importance.csv", index=False)
    write_json(out / "label_rejections.json", rejected)
    schedules = {
        "lightgbm": ranked_schedule(
            test,
            int(config["start"][:4]),
            config["rebalance_weeks"],
            config["minimum_candidates"],
            config["stop_exclusive"],
        )
    }
    for kind in ["momentum60", "equal_groups"]:
        schedules[kind] = ranked_schedule(
            score_control(test, kind),
            int(config["start"][:4]),
            config["rebalance_weeks"],
            config["minimum_candidates"],
            config["stop_exclusive"],
        )
    for seed in config["random_seeds"]:
        schedules[f"random_{seed}"] = ranked_schedule(
            score_control(test, "random", seed),
            int(config["start"][:4]),
            config["rebalance_weeks"],
            config["minimum_candidates"],
            config["stop_exclusive"],
        )
    write_json(out / "schedules.json", schedules)
    result = {
        "training_rows": len(train),
        "training_label_rejections": len(rejected),
        "prediction_rows": len(test),
        "latest_label_available_ms": int(train.label_available_ms.max()),
        "fit_cutoff_ms": cutoff,
        "parameters": config["model_parameters"],
        "shap_additivity_max_error": error,
        "output_hashes": {file.name: sha(file) for file in out.iterdir() if file.is_file()},
        "PnL_computed": False,
    }
    write_json(out / "summary.json", result)
    return result


def held_intervals(schedule, notices, start, last):
    intervals = {}
    days = sorted(schedule)
    for i, day in enumerate(days):
        a = ms(day) + 2 * HOUR
        b = ms(days[i + 1]) + 2 * HOUR if i + 1 < len(days) else last - HOUR
        for symbol, weight in schedule[day].items():
            if not weight:
                continue
            notice = episode_notice(notices, symbol, a)
            end = min(b, notice["exit_ms"]) if notice else b
            if end > a:
                intervals.setdefault(symbol, []).append((a, end))
    return intervals


def inspect_schedule(data, schedule, start, last):
    intervals = held_intervals(schedule, data.notices, start, last)
    problems = []

    def add(symbol, t, kind, reason):
        problems.append({"symbol": symbol, "timestamp_ms": int(t), "kind": kind, "reason": reason})

    def held(symbol, t, pre=False):
        return any(a < t <= b if pre else a <= t < b for a, b in intervals.get(symbol, []))

    previous = set()
    for day, weights in sorted(schedule.items()):
        t = ms(day)
        if data.mark("BTCUSDT", t + 2 * HOUR) is None:
            add("BTCUSDT", t + HOUR, "mark", "execution_check_anchor")
        previous = {
            s
            for s in previous
            if episode_notice(data.notices, s, t + HOUR) is None
            or episode_notice(data.notices, s, t + HOUR)["exit_ms"] > t + HOUR
        }
        for symbol in previous | set(weights):
            if not data.trades[symbol].get(t) or data.trades[symbol][t][0] <= 0:
                add(symbol, t, "trade", "sizing_close")
            if data.vwap(symbol, t + HOUR) is None:
                add(symbol, t + HOUR, "trade", "execution_vwap")
            if data.mark(symbol, t + HOUR) is None:
                add(symbol, t, "mark", "decision_mark")
        previous = set(weights)
    for t in range(start, last + 1, DAY):
        if data.mark("BTCUSDT", t) is None:
            add("BTCUSDT", t - HOUR, "mark", "snapshot_anchor")
        for symbol in intervals:
            if held(symbol, t) and data.mark(symbol, t) is None:
                add(symbol, t - HOUR, "mark", "held_daily_mark")
    for symbol, rows in data.funding.items():
        for t, _ in rows:
            if start <= t <= last and held(symbol, t, True) and data.mark(symbol, t) is None:
                add(symbol, t // HOUR * HOUR - HOUR, "mark", "held_funding_mark")
    for symbol, spans in intervals.items():
        records = data.funding_meta.get(symbol, [])
        known = None
        previous_time = None
        previous_interval = None
        for t, interval in records:
            current = (
                interval
                if interval is not None and np.isfinite(interval) and interval > 0
                else known
            )
            if previous_time is not None and current is not None and previous_interval is not None:
                if t - previous_time > max(current, previous_interval) * HOUR + 1000 and any(
                    a < t and b > previous_time for a, b in spans
                ):
                    add(symbol, previous_time, "funding_gap", "unresolved_observed_schedule_break")
            known = current
            previous_time, previous_interval = t, current
        if records:
            last_time = records[-1][0]
            if previous_interval is None or any(
                b > last_time + (previous_interval or 0) * HOUR + 1000 for a, b in spans
            ):
                add(symbol, last_time, "funding_gap", "unverified_held_funding_tail")
        else:
            add(symbol, start, "funding_gap", "no_recorded_held_funding")
        for key, notice in data.notices.items():
            if (
                notice.get("symbol", key) == symbol
                and any(a < notice["exit_ms"] <= b for a, b in spans)
                and key not in data.exit_prices
            ):
                add(symbol, notice["exit_bar_ms"], "risk_exit", "missing_post_notice_bar")
        if (
            any(a < last - HOUR <= b for a, b in spans)
            and data.vwap(symbol, last - 2 * HOUR) is None
        ):
            add(symbol, last - 2 * HOUR, "trade", "final_vwap")
    return problems


def preflight(root, config, path, data):
    from momentum_data.backtest.engine import instrument

    schedules = load_json(path / "model/schedules.json")
    start, last = ms(config["start"]), ms(config["stop_exclusive"]) - DAY
    client = PublicSources(root / config["public_cache"])
    errors = []
    benchmark_bindings = {}
    from .window_report import spot_benchmark

    for symbol in ["BTCUSDT", "ETHUSDT"]:
        try:
            _, bindings = spot_benchmark(root, config, symbol, start, last)
            benchmark_bindings.update(bindings)
        except Exception as exc:
            errors.append({"symbol": symbol, "reason": "spot_benchmark_source", "error": str(exc)})
    for symbol in data.symbols:
        try:
            instrument(symbol)
        except Exception as exc:
            errors.append(
                {"symbol": symbol, "reason": "instrument_construction", "error": str(exc)}
            )
    missing = {}
    for name, schedule in schedules.items():
        for item in inspect_schedule(data, schedule, start, last):
            key = (item["symbol"], item["kind"], item["timestamp_ms"])
            missing.setdefault(key, item | {"cases": []})["cases"].append(name)
    recovery_path = path / "recovered_bars.jsonl"
    recovered = []
    for key, item in sorted(missing.items()):
        symbol, kind, t = key
        if kind not in {"trade", "mark"}:
            continue
        try:
            row, source = client.bar(symbol, kind, t)
            data.add_bar(symbol, kind, row)
            record = {"symbol": symbol, "kind": kind, "row": row, "source": source}
            with recovery_path.open("a") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            recovered.append(key)
        except Exception as exc:
            errors.append(item | {"error": str(exc)})
    unresolved = []
    for name, schedule in schedules.items():
        unresolved.extend(
            item | {"case": name} for item in inspect_schedule(data, schedule, start, last)
        )
    write_json(path / "preflight_problems.json", errors + unresolved)
    result = {
        "success": not errors and not unresolved,
        "plan_count": len(schedules),
        "symbols_constructed": len(data.symbols),
        "initial_unique_missing_keys": len(missing),
        "newly_recovered_keys": len(recovered),
        "problem_count": len(errors) + len(unresolved),
        "source_bindings": {**client.bindings, **benchmark_bindings},
        "schedule_sha256": sha(path / "model/schedules.json"),
        "recovered_bars_sha256": sha(recovery_path) if recovery_path.exists() else None,
        "PnL_computed": False,
    }
    write_json(path / "preflight.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "source_bindings"}), flush=True)
    return result


def run_cases(root, config, path, data):
    from momentum_data.backtest.engine import simulate

    audit = checked(path, "preflight.json")
    if not audit["success"]:
        raise ValueError("All preflight blockers are in preflight_problems.json")
    if (
        audit["recovered_bars_sha256"]
        and sha(path / "recovered_bars.jsonl") != audit["recovered_bars_sha256"]
    ):
        raise ValueError("Recovered execution bars changed")
    schedules = load_json(path / "model/schedules.json")
    start, last = ms(config["start"]), ms(config["stop_exclusive"]) - DAY
    days = {ms(d) for schedule in schedules.values() for d in schedule}
    events = data.events(start, last, days)
    cases = (
        [
            (name, bps)
            for name in ["lightgbm", "momentum60", "equal_groups"]
            for bps in config["slippage_bps"]
        ]
        + [(f"random_{seed}", 5) for seed in config["random_seeds"]]
        + [("primary_replay", 5)]
    )
    result_rows = []
    for name, bps in cases:
        folder = path / "results" / f"{name}_{bps}bps"
        if (folder / "engine_summary.json").exists() and (folder / "case_manifest.json").exists():
            result = load_json(folder / "engine_summary.json")
            checked(folder, "case_manifest.json")
        else:
            print(f"Nautilus first window: {name}/{bps}bps", flush=True)
            try:
                _, result = simulate(
                    data,
                    events,
                    schedules["lightgbm" if name == "primary_replay" else name],
                    folder,
                    bps=bps,
                )
                write_json(
                    folder / "case_manifest.json",
                    {
                        "output_hashes": {
                            file.name: sha(file)
                            for file in folder.iterdir()
                            if file.is_file() and file.name != "case_manifest.json"
                        },
                        "schedule_sha256": sha(path / "model/schedules.json"),
                        "bps": bps,
                    },
                )
            except Exception as exc:
                folder.mkdir(parents=True, exist_ok=True)
                result = {"success": False, "error": str(exc)}
                write_json(folder / "failure_summary.json", result)
        result_rows.append({"case": name, "bps": bps, **result})
        write_json(
            path / "run_status.json",
            {"completed": len(result_rows), "registered": len(cases), "cases": result_rows},
        )
    primary = (
        load_json(path / "results/lightgbm_5bps/engine_summary.json")
        if (path / "results/lightgbm_5bps/engine_summary.json").exists()
        else {}
    )
    replay = (
        load_json(path / "results/primary_replay_5bps/engine_summary.json")
        if (path / "results/primary_replay_5bps/engine_summary.json").exists()
        else {}
    )
    identical = bool(primary.get("financial_sha256")) and primary.get(
        "financial_sha256"
    ) == replay.get("financial_sha256")
    summary = {
        "success": all(row.get("success") for row in result_rows) and identical,
        "registered_cases": len(cases),
        "completed_cases": len(result_rows),
        "primary_replay_identical": identical,
        "cases": result_rows,
        "event_count": len(events),
        "fresh_OOS": False,
        "window": window_label(config),
    }
    write_json(path / "simulation_summary.json", summary)
    return summary


def main_stage(root, config_path, stage, run_dir=None):
    root, config_path = Path(root), Path(config_path)
    config = load_json(config_path)
    if config["train_stop"] != config["start"]:
        raise ValueError("Training cutoff must equal forecast-year start")
    if run_dir is not None:
        path = Path(run_dir)
        if stage not in {"summary", "report"}:
            raise ValueError("Explicit run-dir is read/report only")
        if load_json(path / "manifest.json")["identity"]["config_sha256"] != sha(config_path):
            raise ValueError("Saved run/config mismatch")
        if stage == "report":
            from .window_report import report

            return report(root, config, path)
        return print_summary(path)
    ident = identity(root, config_path, config)
    key = hashlib.sha256(json.dumps(ident, sort_keys=True).encode()).hexdigest()[:20]
    path = root / config["output_root"] / key
    print("Window output: " + str(path), flush=True)
    if stage == "summary":
        return print_summary(path)
    prepare(root, config, path, ident)
    if stage == "prepare":
        return {"prepared": str(path)}
    if stage == "report":
        from .window_report import report

        return report(root, config, path)
    data = load_data(path)
    fit(root, config, path, data)
    if stage == "fit":
        return {"model": str(path / "model")}
    if stage in {"preflight", "all"}:
        result = preflight(root, config, path, data)
        if not result["success"] or stage == "preflight":
            return result
    if stage in {"simulate", "all"}:
        result = run_cases(root, config, path, data)
        if not result["success"]:
            return result
    from .window_report import report

    return report(root, config, path)


def print_summary(path):
    name = next(
        (
            n
            for n in ["report_summary.json", "simulation_summary.json", "preflight.json"]
            if (path / n).exists()
        ),
        None,
    )
    if name is None:
        raise ValueError("No completed stage summary in " + str(path))
    result = load_json(path / name)
    keys = [
        "success",
        "window",
        "registered_cases_completed",
        "completed_cases",
        "primary_replay_identical",
        "random_comparison",
        "return_excluding_best_month",
        "candidate_comparison",
        "problem_count",
    ]
    compact = {k: result[k] for k in keys if k in result}
    if "primary_metrics" in result:
        compact["primary_metrics"] = [
            {k: row[k] for k in ["series", "total_return", "Sharpe_rf0", "MDD"]}
            for row in result["primary_metrics"]
        ]
    print(json.dumps(compact), flush=True)
    return result
