"""Explicit retrospective accounting scenario; raw features and labels stay unchanged."""

import hashlib
import json
import math
from pathlib import Path

from . import first_window as core
from .config import HOUR, load_json, sha
from .repair import write_json
from .window_data import ms

ASSUMPTIONS = "funding_assumptions.json"


def policy_bounds(config):
    policy = config["funding_imputation"]
    if (
        policy["method"] != "adjacent_mean"
        or policy["use"] != "accounting_only"
        or policy.get("uses_future_anchor") is not True
        or policy["start_utc"] != "2026-06-24"
        or policy["stop_exclusive_utc"] != "2026-06-25"
    ):
        raise ValueError("Unsupported funding assumption; retain the registered scope")
    return ms(policy["start_utc"]), ms(policy["stop_exclusive_utc"])


def mean_records(data, start, stop):
    records = []
    for symbol, events in data.funding_meta.items():
        rates = dict(data.funding[symbol])
        for (a, ha), (b, hb) in zip(events, events[1:], strict=False):
            if ha is None or hb is None or not math.isfinite(ha) or ha != hb or ha <= 0:
                continue
            step = int(round(ha * HOUR))
            if step <= 0 or b - a <= step + 1000:
                continue
            base = a // HOUR * HOUR
            count = int(round((b - base) / step))
            if a - base > 1000 or count <= 1 or abs(b - (base + count * step)) > 1000:
                continue
            times = [base + i * step for i in range(1, count)]
            if not all(start <= t < stop for t in times):
                continue
            before, after = float(rates[a]), float(rates[b])
            if not math.isfinite(before) or not math.isfinite(after):
                raise ValueError("Funding anchors must be finite")
            for t in times:
                if t in rates:
                    raise ValueError("Refusing to overwrite original funding")
                records.append(
                    {
                        "symbol": symbol,
                        "timestamp_ms": t,
                        "rate": (before + after) / 2,
                        "interval_hours": ha,
                        "before_ms": a,
                        "before_rate": before,
                        "after_ms": b,
                        "after_rate": after,
                    }
                )
    return sorted(records, key=lambda row: (row["symbol"], row["timestamp_ms"]))


def apply_assumptions(path, config, data):
    start, stop = policy_bounds(config)
    records = mean_records(data, start, stop)
    payload = {
        "method": "adjacent_mean",
        "use": "accounting_only",
        "uses_future_anchor": True,
        "start_ms": start,
        "stop_exclusive_ms": stop,
        "original_funding_sha256": sha(path / "funding.parquet"),
        "records": records,
        "estimated_events": len(records),
    }
    target = path / ASSUMPTIONS
    if target.exists() and load_json(target) != payload:
        raise ValueError("Saved funding assumptions differ; do not overwrite scenario evidence")
    write_json(target, payload)
    for row in records:
        symbol, t = row["symbol"], row["timestamp_ms"]
        data.funding[symbol].append((t, row["rate"]))
        data.funding_meta[symbol].append((t, row["interval_hours"]))
    for symbol in {r["symbol"] for r in records}:
        data.funding[symbol].sort()
        data.funding_meta[symbol].sort()
    return payload


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
        raise ValueError("No completed mean-funding stage summary")
    result = load_json(path / name)
    compact = {
        k: v
        for k, v in result.items()
        if k
        not in {
            "source_bindings",
            "output_hashes",
            "cases",
            "random_control_summary",
        }
    }
    compact.setdefault(
        "funding_imputation",
        {
            "method": "adjacent_mean",
            "use": "accounting_only",
            "uses_future_anchor": True,
        },
    )
    print(json.dumps(compact), flush=True)
    return result


def main_stage(root, config_path, stage, run_dir=None):
    root, config_path = Path(root), Path(config_path)
    config = load_json(config_path)
    policy_bounds(config)
    if config["train_stop"] != config["start"]:
        raise ValueError("Training cutoff must equal forecast-year start")
    if run_dir is not None:
        path = Path(run_dir)
        if stage not in {"report", "summary"}:
            raise ValueError("Explicit run-dir is read/report only")
        if load_json(path / "manifest.json")["identity"]["config_sha256"] != sha(config_path):
            raise ValueError("Saved run/config mismatch")
    else:
        ident = core.identity(root, config_path, config)
        ident["mean_funding_code_sha256"] = sha(Path(__file__))
        key = hashlib.sha256(json.dumps(ident, sort_keys=True).encode()).hexdigest()[:20]
        path = root / config["output_root"] / key
        print("Window output: " + str(path), flush=True)
    if stage == "summary":
        return print_summary(path)
    if stage == "report":
        from .window_report import report

        return report(root, config, path)
    core.prepare(root, config, path, ident)
    if stage == "prepare":
        return {"prepared": str(path)}
    data = core.load_data(path)
    # Keep all estimation out of fitting, labels, factors and ranked schedules.
    core.fit(root, config, path, data)
    if stage == "fit":
        return {"model": str(path / "model")}
    assumptions = apply_assumptions(path, config, data)
    print(
        json.dumps(
            {
                "funding_imputation": "adjacent_mean",
                "estimated_events": assumptions["estimated_events"],
                "uses_future_anchor": True,
            }
        ),
        flush=True,
    )
    if stage in {"preflight", "all"}:
        result = core.preflight(root, config, path, data)
        result["source_bindings"][str((path / ASSUMPTIONS).resolve())] = sha(path / ASSUMPTIONS)
        result["funding_imputation"] = {
            "method": "adjacent_mean",
            "estimated_events": assumptions["estimated_events"],
            "uses_future_anchor": True,
        }
        write_json(path / "preflight.json", result)
        if not result["success"] or stage == "preflight":
            return result
    if stage in {"simulate", "all"}:
        result = core.run_cases(root, config, path, data)
        for case in result["cases"]:
            target = path / "results" / f"{case['case']}_{case['bps']}bps/case_manifest.json"
            if target.exists():
                manifest = load_json(target)
                manifest.setdefault("source_bindings", {})[str((path / ASSUMPTIONS).resolve())] = (
                    sha(path / ASSUMPTIONS)
                )
                write_json(target, manifest)
        if not result["success"]:
            return result
    del data
    from .window_report import report

    return report(root, config, path)
