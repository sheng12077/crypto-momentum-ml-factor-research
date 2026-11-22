"""User-run final holdout input preparation; immutable old cache, no performance."""
import csv
import io
import json
import math
import zipfile

import pandas as pd
import pyarrow.parquet as pq
from audit_development_continuity import DEV_COLUMNS, sha
from final_holdout_acquisition import Archives
from final_holdout_common import (
    BASE, DAY, OLD, PREPARED, START, STOP, bind, checked_manifest,
    code_contract, features_for_dates, mondays, months, write,
)
from prepare_first_development import DAILY, load_hours
from prepare_validation_2024 import defaultdict_rows
from final_holdout_lifecycle import filter_terminal_rows, inherit_source_caches, repair_pair, terminal_boundaries
from reconcile_mark_gaps import parse_payload


class Repair:
    def __init__(self):
        self.client = Archives(BASE / "repair/raw", 400, 64*1024**2, 200)
        self.sources = []

    def fetch(self, symbol, kind, day):
        from final_holdout_common import ms
        start = ms(day)
        if not START <= start < STOP:
            raise ValueError("Repair beyond authorized dates")
        part = "klines" if kind == "trade" else "markPriceKlines"
        filename = f"{symbol}-1h-{day}.zip"
        url = f"https://data.binance.vision/data/futures/um/daily/{part}/{symbol}/1h/{filename}"
        body, meta = self.client.fetch(f"{kind}/{symbol}/{day}", url)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            if archive.namelist() != [filename[:-4]+".csv"] or archive.infolist()[0].file_size > 10*1024**2:
                raise ValueError("Unexpected repair ZIP member")
            raw = [r for r in csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode("utf-8-sig")))
                   if r and r[0] != "open_time"]
        parse_payload(json.dumps(raw).encode(), symbol, start, start+DAY-1)
        result = {}
        for r in raw:
            item = {"bar_open_ms": int(r[0]), "close": float(r[4])}
            if kind == "trade":
                item.update(volume=float(r[5]), quote_volume=float(r[7]), taker_buy_quote_volume=float(r[10]))
                if not all(math.isfinite(item[k]) and item[k] >= 0 for k in (
                        "volume", "quote_volume", "taker_buy_quote_volume")):
                    raise ValueError("Invalid repair volumes")
                if item["taker_buy_quote_volume"] > item["quote_volume"]*(1+1e-9):
                    raise ValueError("Invalid repair imbalance")
            result[item["bar_open_ms"]] = item
        self.sources.append({"symbol": symbol, "kind": kind, "day": day, **meta})
        return result


def prepare():
    bind(BASE / "code_contract.json", code_contract())
    from final_holdout_migration import migrate_engine_fix
    migrate_engine_fix(BASE)
    inherit_source_caches(BASE)
    old_meta = checked_manifest(OLD)
    if (PREPARED / "manifest.json").exists():
        meta = checked_manifest(PREPARED)
        if meta["code_contract_sha256"] != sha(BASE / "code_contract.json"):
            raise ValueError("Prepared contract mismatch")
        for name, hashes in json.loads((PREPARED / "source_bindings.json").read_text()).items():
            if name.startswith("daily/"):
                symbol = name.split("/")[1]
                if sha(DAILY / "daily" / f"{symbol}.parquet") != hashes["daily"]:
                    raise ValueError("Canonical daily source changed")
        print(json.dumps({"success": True, "stage": "prepare", "cache_hit": True}))
        return
    symbols, bindings, repairs = old_meta["symbols"], {}, {}
    if len(symbols) != 37:
        raise ValueError("Frozen cohort changed")
    boundaries = terminal_boundaries(symbols)
    boundary_audit = {}
    additions = {k: [] for k in ("trade", "mark", "funding")}
    features, repair = [], Repair()
    for i, symbol in enumerate(symbols, 1):
        path, ip = DAILY / "daily" / f"{symbol}.parquet", DAILY / "index" / f"{symbol}.json"
        index = json.loads(ip.read_text())
        if sha(path) != index["daily_sha256"]:
            raise ValueError("Canonical daily source changed")
        bindings[f"daily/{symbol}"] = {"index": sha(ip), "daily": sha(path),
            "loaded_range": ["2024-08-01", "2026-11-01"]}
        columns = sorted(set(DEV_COLUMNS+["trade_quote_volume_sum", "trade_volume_sum", "taker_buy_quote_volume_sum"]))
        rows = pq.read_table(path, columns=columns, filters=[("data_day", ">=", "2024-08-01"),
            ("data_day", "<", "2026-11-01")]).to_pylist()
        products = {k: [] for k in additions}
        for kind, target in products.items():
            for month in months():
                target += load_hours(symbol, kind, month, index, False, bindings)
        products, boundary_audit[symbol] = filter_terminal_rows(symbol, products, boundaries.get(symbol))
        write(BASE / "repair/terminal_boundary_audit.json", boundary_audit)
        trades, marks, changed, counts = repair_pair(symbol, products["trade"], products["mark"], repair,
                                                   BASE / "repair/unresolved")
        repairs[symbol] = counts
        grouped = defaultdict_rows(trades)
        for r in rows:
            if r["data_day"] not in changed:
                continue
            g = grouped[r["data_day"]]
            if len(g) != 24:
                if r["partial_lifecycle_day"] or r["known_lifecycle_order_block"]:
                    continue  # Preserve lifecycle failure flags; never turn this into a full eligible day.
                raise ValueError(f"Recovered active trade day incomplete: {symbol}/{r['data_day']}")
            r.update(trade_hours=24, trade_close=g[-1]["close"], trade_volume_sum=math.fsum(v["volume"] for v in g),
                trade_quote_volume_sum=math.fsum(v["quote_volume"] for v in g),
                taker_buy_quote_volume_sum=math.fsum(v["taker_buy_quote_volume"] for v in g), imbalance_inputs_valid=True)
            r["trade_close_valid_for_history"] = bool(r["trade_volume_sum"] > 0 and r["trade_close"] > 0
                and r["episode_number"] == r["close_episode_number"] and not r["known_lifecycle_order_block"])
            r["base_failure_mask"] &= ~(1 | 4)
        funding = pd.read_parquet(OLD / "funding.parquet", filters=[("instrument_id", "==", symbol)]).drop(
            columns="instrument_id").to_dict("records")+products["funding"]
        funding.sort(key=lambda v: v["event_timestamp_ms"])
        if len({v["event_timestamp_ms"] for v in funding}) != len(funding):
            raise ValueError("Duplicate funding events")
        warm = pd.read_parquet(OLD / "mark.parquet", filters=[("instrument_id", "==", symbol),
            ("bar_open_ms", ">=", START-7*DAY)]).drop(columns="instrument_id").to_dict("records")
        features += features_for_dates(rows, warm+marks, funding, symbol, mondays(2025)+mondays(2026))
        for kind, values in (("trade", trades), ("mark", marks), ("funding", products["funding"])):
            additions[kind] += [{"instrument_id": symbol, **v} for v in values]
        print(f"prepare {i}/{len(symbols)} {symbol} missing_keys={counts}", flush=True)
    PREPARED.mkdir(parents=True, exist_ok=True)
    for kind, extra in additions.items():
        key = "event_timestamp_ms" if kind == "funding" else "bar_open_ms"
        new = pd.DataFrame(extra)
        if ((new[key] < START) | (new[key] >= STOP)).any():
            raise ValueError("Out-of-scope appended source")
        old = pd.read_parquet(OLD / f"{kind}.parquet")
        merged = pd.concat([old, new], ignore_index=True)
        if merged.duplicated(["instrument_id", key]).any():
            raise ValueError("Duplicate merged observation")
        merged.to_parquet(PREPARED / f"{kind}.parquet", index=False)
    old = pd.read_parquet(OLD / "features.parquet")
    new_features = pd.DataFrame(features, columns=old.columns).astype(old.dtypes.to_dict())
    frame = pd.concat([old, new_features], ignore_index=True)
    pd.testing.assert_frame_equal(frame.iloc[:len(old)], old.reset_index(drop=True), check_exact=True)
    if frame.loc[frame.feature_cutoff_ms >= START, "label"].notna().any():
        raise ValueError("Holdout feature table must remain unlabelled")
    frame.to_parquet(PREPARED / "features.parquet", index=False)
    write(PREPARED / "source_bindings.json", bindings)
    write(BASE / "repair/sources.json", repair.sources)
    write(PREPARED / "manifest.json", {"success": True, "symbols": symbols,
        "code_contract_sha256": sha(BASE / "code_contract.json"), "prior_features_labels_preserved": True,
        "holdout_feature_rows": len(features), "holdout_labels_computed": False,
        "model_fitted": False, "PnL_computed": False, "source_repairs": repairs,
        "terminal_boundaries": boundaries, "terminal_archive_tails_quarantined": True,
        "output_hashes": {p.name: sha(p) for p in PREPARED.iterdir() if p.is_file() and p.name != "manifest.json"}})
    print(json.dumps({"success": True, "stage": "prepare", "holdout_rows": len(features)}))


if __name__ == "__main__":
    prepare()
