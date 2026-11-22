"""Experiment013: append verified2024 data without changing corrected training rows."""

import csv
import io
import json
import math
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from acquire_usdm_universe import verify_payload
from audit_development_continuity import DEV_COLUMNS, sha
from development_continuity_rules import normalized, numeric_history
from prepare_first_development import DAILY, DAY, FEATURES, HOUR, ROOT, funding_feature, load_hours
from reconcile_mark_gaps import ProbeClient, parse_payload
from recover_development_marks import Pace

BASE = ROOT / "data/interim/validation_2024/v20261121_002"
OLD = ROOT / "data/interim/validation_2023/v20261121_001/prepared"
PREPARED = BASE / "prepared"
START = 1704067200000
END = 1735689600000


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def calendar():
    return [date(2024, 1, 1) + timedelta(days=7*i) for i in range(53)]


def training_labels(frame, trades):
    """Add only matured pre-2024 labels; never evaluate a 2024 execution price."""
    result = frame.copy()
    lookup = {(r.instrument_id, int(r.bar_open_ms)): r for r in trades.itertuples()}
    for row in result.itertuples():
        if not (pd.Timestamp("2023-01-01", tz="UTC").timestamp()*1000
                <= row.feature_cutoff_ms < START and row.label_available_ms < START):
            continue
        entry = int(row.feature_cutoff_ms) + HOUR
        exit_time = entry + 7*DAY
        if exit_time + 2*HOUR != row.label_available_ms or exit_time >= START:
            raise ValueError("Training label availability mismatch")
        a, b = lookup.get((row.instrument_id, entry)), lookup.get((row.instrument_id, exit_time))
        if a is not None and b is not None and a.volume > 0 and b.volume > 0:
            label = (b.quote_volume/b.volume)/(a.quote_volume/a.volume)-1
            if not math.isfinite(label):
                raise ValueError("Nonfinite training label")
            result.loc[row.Index, "label"] = label
    pd.testing.assert_frame_equal(result.drop(columns="label"), frame.drop(columns="label"), check_exact=True)
    prior = frame.feature_cutoff_ms < int(pd.Timestamp("2023-01-01", tz="UTC").timestamp()*1000)
    pd.testing.assert_series_equal(result.loc[prior, "label"], frame.loc[prior, "label"], check_exact=True)
    if result.loc[result.feature_cutoff_ms >= START, "label"].notna().any():
        raise ValueError("Validation labels must remain absent")
    return result


def append_features(rows, marks, funding, symbol):
    """All features use days before Monday;2024 labels are deliberately absent."""
    points = [normalized(r) for r in rows]
    history = numeric_history(points)
    normalized_days = {p["day"]: p for p in points}
    by_day = {date.fromisoformat(r["data_day"]): r for r in rows}
    counts = pd.Series([r["bar_open_ms"] // DAY for r in marks]).value_counts().to_dict()
    features = []
    for decision in calendar():
        cutoff = int(pd.Timestamp(decision, tz="UTC").timestamp() * 1000)
        day = decision - timedelta(days=1)
        row = by_day.get(day)
        recent = [by_day.get(day - timedelta(days=i)) for i in range(7)]
        imbalance_valid = all(recent) and all(normalized_days[day-timedelta(days=i)]["imbalance"] for i in range(7))
        rate = funding_feature(funding, cutoff)
        if not (row and history[day] >= 121 and counts.get((cutoff-DAY)//DAY, 0) == 24
                and imbalance_valid and (row["base_failure_mask"] & ~(8 | 2)) == 0 and rate is not None):
            continue
        quote = math.fsum(r["trade_quote_volume_sum"] for r in recent)
        buy = math.fsum(r["taker_buy_quote_volume_sum"] for r in recent)
        if quote <= 0:
            continue
        item = {"instrument_id": symbol, "decision_date": decision.isoformat(),
                "feature_cutoff_ms": cutoff, "decision_ms": cutoff+HOUR,
                "label_available_ms": cutoff+3*HOUR+7*DAY, "label": None,
                "funding7": rate, "imbalance7": 2*buy/quote-1}
        for horizon in (20, 60, 120):
            item[f"momentum{horizon}"] = row["trade_close"] / by_day[day-timedelta(days=horizon)]["trade_close"] - 1
        if not all(math.isfinite(item[k]) for k in FEATURES):
            raise ValueError("Nonfinite2024feature")
        features.append(item)
    return features


class Repair:
    def __init__(self):
        self.pace = Pace()
        self.requests = self.compressed = self.jobs = 0
        self.sources = []

    def fetch(self, symbol, kind, day):
        self.jobs += 1
        if self.jobs > 200:
            raise ValueError("Registered200repair-source-day budget exceeded")
        part = "klines" if kind == "trade" else "markPriceKlines"
        filename = f"{symbol}-1h-{day}.zip"
        url = f"https://data.binance.vision/data/futures/um/daily/{part}/{symbol}/1h/{filename}"
        folder = BASE / "repair/raw" / kind / symbol / day
        folder.mkdir(parents=True, exist_ok=True)
        if (folder / "source.json").exists():
            meta = json.loads((folder / "source.json").read_text())
            body, checksum = (folder / "archive.zip").read_bytes(), (folder / "checksum.txt").read_bytes()
            if meta["url"] != url or sha(folder / "archive.zip") != meta["sha256"]:
                raise ValueError("Repair cache binding mismatch")
        else:
            if self.requests + 2 > 400:
                raise ValueError("Repair request budget exceeded")
            attempt = folder / datetime.now(UTC).strftime("attempt_%Y%m%dT%H%M%S%fZ")
            client = ProbeClient(attempt)
            try:
                self.pace.wait()
                checksum = client.get("checksum", url + ".CHECKSUM", 4096)
                self.pace.wait()
                body = client.get("archive", url, 2*1024**2)
                self.requests += 2
            finally:
                write(attempt / "manifest.json", client.manifest)
            verify_payload(body, checksum, filename, len(body))
            (folder / "archive.zip").write_bytes(body)
            (folder / "checksum.txt").write_bytes(checksum)
            meta = {"url": url, "sha256": sha(folder / "archive.zip"),
                    "retrieved_at": client.manifest[-1]["retrieved_at"]}
            write(folder / "source.json", meta)
        verify_payload(body, checksum, filename, len(body))
        self.compressed += len(body)
        if self.compressed > 64*1024**2:
            raise ValueError("Repair byte budget exceeded")
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            if archive.namelist() != [filename[:-4]+".csv"] or archive.infolist()[0].file_size > 10*1024**2:
                raise ValueError("Unexpected repair ZIP structure/size")
            raw = [r for r in csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode("utf-8-sig")))
                   if r and r[0] != "open_time"]
        start = int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp()*1000)
        if not START <= start < END:
            raise ValueError("Repair outside2024scope")
        parse_payload(json.dumps(raw).encode(), symbol, start, start+DAY-1)
        result = {}
        for r in raw:
            item = {"bar_open_ms": int(r[0]), "close": float(r[4])}
            if kind == "trade":
                item.update(volume=float(r[5]), quote_volume=float(r[7]), taker_buy_quote_volume=float(r[10]))
                if not all(math.isfinite(item[k]) and item[k] >= 0 for k in ("volume", "quote_volume", "taker_buy_quote_volume")):
                    raise ValueError("Invalid recovered volumes")
                if item["taker_buy_quote_volume"] > item["quote_volume"]*(1+1e-9):
                    raise ValueError("Invalid taker buy quote bound")
            result[item["bar_open_ms"]] = item
        self.sources.append({"symbol": symbol, "kind": kind, "day": day, **meta})
        return result


def repair_pair(symbol, trades, marks, repair):
    maps = {"trade": {r["bar_open_ms"]: r for r in trades}, "mark": {r["bar_open_ms"]: r for r in marks}}
    if len(maps["trade"]) != len(trades) or len(maps["mark"]) != len(marks):
        raise ValueError("Duplicate2024hour keys")
    repaired_days, counts = set(), {}
    for kind, counterpart in (("trade", "mark"), ("mark", "trade")):
        missing = set(maps[counterpart]) - set(maps[kind])
        counts[kind] = len(missing)
        days = sorted({datetime.fromtimestamp(t/1000, UTC).strftime("%Y-%m-%d") for t in missing})
        for day in days:
            recovered = repair.fetch(symbol, kind, day)
            for stamp, row in recovered.items():
                if stamp in maps[kind]:
                    for key in ("close", "volume", "quote_volume"):
                        if key in row and not np.isclose(row[key], maps[kind][stamp][key], rtol=1e-12, atol=1e-12):
                            raise ValueError("Repair conflicts with original source")
                elif stamp in missing:
                    maps[kind][stamp] = row
                    if kind == "trade":
                        repaired_days.add(day)
            if any(t not in maps[kind] for t in missing if datetime.fromtimestamp(t/1000, UTC).strftime("%Y-%m-%d") == day):
                raise ValueError("Unresolved requested repair keys")
    return ([maps["trade"][t] for t in sorted(maps["trade"])],
            [maps["mark"][t] for t in sorted(maps["mark"])], repaired_days, counts)


def prepare():
    old_meta = json.loads((OLD / "manifest.json").read_text())
    for name, digest in old_meta["output_hashes"].items():
        if sha(OLD / name) != digest:
            raise ValueError("Original corrected cache changed")
    if (PREPARED / "manifest.json").exists():
        meta = json.loads((PREPARED / "manifest.json").read_text())
        if meta["script_sha256"] != sha(Path(__file__)):
            raise ValueError("Prepared2024 version bound to different code")
        for name, digest in meta["output_hashes"].items():
            if sha(PREPARED / name) != digest:
                raise ValueError("Prepared2024 cache changed")
        print(json.dumps({"success": True, "cache_hit": True}), flush=True)
        return
    symbols = old_meta["symbols"]
    bindings, all_trade, all_mark, all_funding, features, daily_out = {}, [], [], [], [], []
    repair = Repair()
    repairs = {}
    for i, symbol in enumerate(symbols, 1):
        path = DAILY / "daily" / f"{symbol}.parquet"
        index_path = DAILY / "index" / f"{symbol}.json"
        index = json.loads(index_path.read_text())
        if sha(path) != index["daily_sha256"]:
            raise ValueError("Daily source changed")
        bindings[f"daily/{symbol}"] = {"index": sha(index_path), "daily": sha(path),
                                        "loaded_range": ["2023-08-01", "2025-01-01"]}
        columns = list(set(DEV_COLUMNS + ["trade_quote_volume_sum", "trade_volume_sum", "taker_buy_quote_volume_sum"]))
        rows = pq.read_table(path, columns=columns, filters=[("data_day", ">=", "2023-08-01"),
                                                            ("data_day", "<", "2025-01-01")]).to_pylist()
        products = {"trade": [], "mark": [], "funding": []}
        for kind, target in products.items():
            for month in range(1, 13):
                target += load_hours(symbol, kind, f"2024-{month:02d}", index, False, bindings)
        trades, marks, changed, counts = repair_pair(symbol, products["trade"], products["mark"], repair)
        repairs[symbol] = counts
        by_trade_day = defaultdict_rows(trades)
        for row in rows:
            if row["data_day"] not in changed:
                continue
            group = by_trade_day[row["data_day"]]
            if len(group) != 24:
                raise ValueError("Recovered trade day incomplete")
            row.update(trade_hours=24, trade_close=group[-1]["close"], trade_volume_sum=math.fsum(r["volume"] for r in group),
                       trade_quote_volume_sum=math.fsum(r["quote_volume"] for r in group),
                       taker_buy_quote_volume_sum=math.fsum(r["taker_buy_quote_volume"] for r in group), imbalance_inputs_valid=True)
            row["trade_close_valid_for_history"] = bool(row["trade_volume_sum"] > 0 and row["trade_close"] > 0
                and row["episode_number"] == row["close_episode_number"] and not row["known_lifecycle_order_block"])
            row["base_failure_mask"] &= ~(1 | 4)
        old_funding = pd.read_parquet(OLD / "funding.parquet", filters=[("instrument_id", "==", symbol)])
        funding = old_funding.drop(columns="instrument_id").to_dict("records") + products["funding"]
        funding.sort(key=lambda r: r["event_timestamp_ms"])
        if len({r["event_timestamp_ms"] for r in funding}) != len(funding):
            raise ValueError("Duplicate funding event")
        #2023 rows supply warmup; original corrected feature table supplies training.
        old_marks = pd.read_parquet(OLD / "mark.parquet", filters=[("instrument_id", "==", symbol),
                                                                 ("bar_open_ms", ">=", START-7*DAY)])
        feature_marks = old_marks.drop(columns="instrument_id").to_dict("records") + marks
        features += append_features(rows, feature_marks, funding, symbol)
        all_trade += [{"instrument_id": symbol, **r} for r in trades]
        all_mark += [{"instrument_id": symbol, **r} for r in marks]
        all_funding += [{"instrument_id": symbol, **r} for r in products["funding"]]
        daily_out += [{"instrument_id": symbol, "data_day": r["data_day"], "trade_close": r["trade_close"]}
                      for r in rows if r["data_day"] >= "2024-01-01"]
        print(f"2024 preparation {i}/{len(symbols)} {symbol} repair={counts}", flush=True)
    PREPARED.mkdir(parents=True, exist_ok=True)
    for name, additional, key in [("trade", all_trade, "bar_open_ms"), ("mark", all_mark, "bar_open_ms"),
                                  ("funding", all_funding, "event_timestamp_ms")]:
        old = pd.read_parquet(OLD / f"{name}.parquet")
        new = pd.DataFrame(additional)
        if ((new[key] < START) | (new[key] >= END)).any():
            raise ValueError("Appended source outside2024")
        merged = pd.concat([old, new], ignore_index=True)
        if merged.duplicated(["instrument_id", key]).any():
            raise ValueError("Duplicate merged observation")
        merged.to_parquet(PREPARED / f"{name}.parquet", index=False)
    old = pd.read_parquet(OLD / "features.parquet")
    labelled = training_labels(old, pd.read_parquet(OLD / "trade.parquet"))
    frame = pd.concat([labelled, pd.DataFrame(features)[old.columns]], ignore_index=True)
    pd.testing.assert_frame_equal(frame.iloc[:len(old)].reset_index(drop=True), labelled.reset_index(drop=True),
                                  check_exact=True, check_dtype=False)
    frame.to_parquet(PREPARED / "features.parquet", index=False)
    pd.DataFrame(daily_out).to_parquet(PREPARED / "daily2024.parquet", index=False)
    write(PREPARED / "source_bindings.json", bindings)
    write(BASE / "repair/sources.json", repair.sources)
    coverage = pd.DataFrame(features).groupby("decision_date").size().reindex([d.isoformat() for d in calendar()], fill_value=0)
    report = {"success": True, "symbols": symbols, "script_sha256": sha(Path(__file__)),
              "registration_sha256": sha(ROOT / "experiments/013_frozen_2024_validation.md"),
              "original_prepared_sha256": sha(OLD / "manifest.json"), "pre_2023_training_rows_exactly_preserved": True,
              "pre_2024_features_exactly_preserved": True,
              "matured_2023_labels_added": int(labelled.label.notna().sum()-old.label.notna().sum()),
              "validation_2024_rows": len(features), "weekly_candidate_counts": coverage.to_dict(),
              "source_repairs": repairs, "repair_requests": repair.requests, "repair_days": repair.jobs,
              "validation_labels_computed": False, "model_fitted": False, "PnL_computed": False,
              "final_2025_2026_OOS_inspected": False,
              "output_hashes": {p.name: sha(p) for p in PREPARED.iterdir() if p.name != "manifest.json"}}
    write(PREPARED / "manifest.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("output_hashes", "symbols", "source_repairs", "weekly_candidate_counts")}), flush=True)


def defaultdict_rows(rows):
    result = {}
    for row in rows:
        day = datetime.fromtimestamp(row["bar_open_ms"]/1000, UTC).strftime("%Y-%m-%d")
        result.setdefault(day, []).append(row)
    return result


if __name__ == "__main__":
    prepare()
