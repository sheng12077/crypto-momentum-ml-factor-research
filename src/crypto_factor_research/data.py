"""Verified daily and funding readers independent of archived script code."""

import hashlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .config import load_json, sha

DAILY_COLUMNS = [
    "instrument_id",
    "data_day",
    "reference_time_ms",
    "episode_number",
    "close_episode_number",
    "trade_hours",
    "mark_hours",
    "trade_close",
    "mark_close",
    "trade_volume_sum",
    "trade_quote_volume_sum",
    "taker_buy_quote_volume_sum",
    "trade_close_valid_for_history",
    "imbalance_inputs_valid",
    "partial_lifecycle_day",
    "known_lifecycle_order_block",
    "scoped_execution_block",
    "known_equity_episode",
    "lifecycle_origin_unverified",
]
FUND_COLUMNS = ["instrument_id", "event_timestamp_ms", "funding_rate", "funding_interval_hours"]


class Catalog:
    def __init__(self, spec):
        self.spec = spec
        self.daily = spec.path("daily_root")
        self.hourly = spec.path("hourly_root")
        self.manifest = load_json(self.daily / "manifest.json")
        self.symbols = sorted(p.stem for p in (self.daily / "daily").glob("*.parquet"))
        if len(self.symbols) != int(self.manifest["identifiers"]):
            raise ValueError("Full daily catalog/file count mismatch")
        self.indices = {}
        self.index_errors = {}
        self.bindings = {}
        for symbol in self.symbols:
            path = self.daily / "index" / (symbol + ".json")
            try:
                self.indices[symbol] = load_json(path)
                self.bindings[str(path)] = sha(path)
            except Exception as exc:
                self.index_errors[symbol] = str(exc)

    def source_identity(self):
        return {
            "daily_manifest": sha(self.daily / "manifest.json"),
            "hourly_manifest": sha(self.hourly / "manifest.json"),
            "daily_indices": {
                s: self.bindings[str(self.daily / "index" / (s + ".json"))] for s in self.indices
            },
            "missing_indices": self.index_errors,
        }

    def daily_frame(self, symbol):
        if symbol in self.index_errors:
            raise ValueError("Daily index unreadable: " + self.index_errors[symbol])
        index = self.indices[symbol]
        path = self.daily / "daily" / (symbol + ".parquet")
        digest = sha(path)
        if index["instrument_id"] != symbol or digest != index["daily_sha256"]:
            raise ValueError("Daily source identity/checksum mismatch")
        self.bindings[str(path)] = digest
        frame = pq.read_table(path, columns=DAILY_COLUMNS).to_pandas()
        expected = pd.date_range(
            self.spec.values["source_start"],
            self.spec.values["source_stop"],
            inclusive="left",
            tz="UTC",
            freq="D",
        )
        dates = pd.DatetimeIndex(pd.to_datetime(frame.data_day, utc=True))
        if (
            len(frame) != index["rows"]
            or not dates.equals(expected)
            or set(frame.instrument_id) != {symbol}
        ):
            raise ValueError("Daily source row,identifier or date grid mismatch")
        expected_reference = dates.as_unit("ms").asi8 + 86_400_000
        if not np.array_equal(frame.reference_time_ms.to_numpy(), expected_reference):
            raise ValueError("Daily availability reference differs from next midnight")
        return frame.reset_index(drop=True)

    def funding_frame(self, symbol):
        index = self.indices[symbol]
        frames = []
        for key, source in sorted(index["sources"].items()):
            if "/fundingRate/" not in key:
                continue
            month = key.rsplit("-", 2)[-2] + "-" + key.rsplit("-", 1)[-1][:-4]
            rel = f"observations/funding/{symbol}/{month}.parquet"
            meta_path = self.hourly / "index" / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            path = self.hourly / rel
            meta_hash = sha(meta_path)
            meta = load_json(meta_path)
            body_hash = sha(path)
            if (
                meta_hash != source["index_sha256"]
                or body_hash != source["parquet_sha256"]
                or meta["relative_path"] != rel
            ):
                raise ValueError("Funding source/index binding mismatch: " + key)
            if meta["parquet_sha256"] != body_hash or meta["raw_sha256"] != source["raw_sha256"]:
                raise ValueError("Funding raw provenance mismatch: " + key)
            part = pq.read_table(path, columns=FUND_COLUMNS).to_pandas()
            if len(part) != meta["rows"] or (len(part) and set(part.instrument_id) != {symbol}):
                raise ValueError("Funding row/identifier mismatch: " + key)
            self.bindings[str(meta_path)] = meta_hash
            self.bindings[str(path)] = body_hash
            frames.append(part)
        if not frames:
            return pd.DataFrame(
                {
                    "instrument_id": pd.Series(dtype="str"),
                    "event_timestamp_ms": pd.Series(dtype="int64"),
                    "funding_rate": pd.Series(dtype="float64"),
                    "funding_interval_hours": pd.Series(dtype="float64"),
                }
            )
        result = (
            pd.concat(frames, ignore_index=True)
            .sort_values("event_timestamp_ms")
            .reset_index(drop=True)
        )
        if result.event_timestamp_ms.duplicated().any():
            raise ValueError("Duplicate funding timestamps across source partitions")
        return result
