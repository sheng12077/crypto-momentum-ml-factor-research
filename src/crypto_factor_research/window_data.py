"""Explicit first-window observations and public recovery; no frozen-universe readers."""

import csv
import hashlib
import io
import json
import math
import urllib.parse
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .config import DAY, HOUR, load_json, sha
from .repair import RateGate, request, write_json

MINUTE = 60000


def ms(value):
    return int(pd.Timestamp(value).tz_localize("UTC").timestamp() * 1000)


def text_nodes(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "text":
                yield str(item)
            else:
                yield from text_nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from text_nodes(item)


class PublicSources:
    def __init__(self, folder, budget=1200):
        self.folder = Path(folder)
        self.gate = RateGate()
        self.budget = budget
        self.requests = 0
        self.bindings = {}

    def get(self, url):
        key = hashlib.sha256(url.encode()).hexdigest()
        folder = self.folder / key
        meta_path = folder / "source.json"
        if meta_path.exists():
            meta = load_json(meta_path)
            if meta["url"] != url or sha(meta["path"]) != meta["sha256"]:
                raise ValueError("Public source cache changed")
            body = Path(meta["path"]).read_bytes()
        else:
            if self.requests >= self.budget:
                raise ValueError("Public request budget exhausted")
            self.requests += 1
            body, meta = request(url, folder, self.gate)
            write_json(meta_path, meta)
        self.bindings[meta["path"]] = meta["sha256"]
        return body, meta

    def notice(self, item):
        code = item["article_code"]
        body, source = self.get(
            "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode="
            + code
        )
        payload = json.loads(body)
        article = payload["data"]
        text = " ".join(text_nodes(json.loads(article["body"])))
        symbol = item["symbol"]
        if (
            not payload.get("success")
            or article["code"] != code
            or "Futures" not in text
            or symbol.removesuffix("USDT") not in text
            or item["effective_utc"][:10] not in text
        ):
            raise ValueError("Futures notice identity/effective date not verified:" + symbol)
        published = int(article["publishDate"])
        effective = int(pd.Timestamp(item["effective_utc"]).timestamp() * 1000)
        order = ((published + 5 * MINUTE + MINUTE - 1) // MINUTE) * MINUTE
        fill = order + MINUTE
        if not published < order < fill < effective:
            raise ValueError("Notice cannot support an exit before cessation:" + symbol)
        return {
            **item,
            "published_ms": published,
            "blocked_from_ms": published + 5 * MINUTE,
            "exit_bar_ms": order,
            "exit_ms": fill,
            "effective_ms": effective,
            "source": source,
        }

    def bar(self, symbol, kind, start, interval="1h"):
        step = HOUR if interval == "1h" else MINUTE
        endpoint = "markPriceKlines" if kind == "mark" else "klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start,
            "endTime": start + step - 1,
            "limit": 5,
        }
        url = "https://fapi.binance.com/fapi/v1/" + endpoint + "?" + urllib.parse.urlencode(params)
        try:
            body, source = self.get(url)
            rows = json.loads(body)
            if isinstance(rows, list) and len(rows) == 1:
                return validate_bar(rows[0], start, step), source
        except (ValueError, KeyError):
            pass
        day = pd.Timestamp(start, unit="ms", tz="UTC").strftime("%Y-%m-%d")
        filename = f"{symbol}-{interval}-{day}.zip"
        relative = f"data/futures/um/daily/{'markPriceKlines' if kind == 'mark' else 'klines'}/{symbol}/{interval}/{filename}"
        url = "https://data.binance.vision/" + urllib.parse.quote(relative, safe="/")
        proof, proof_meta = self.get(url + ".CHECKSUM")
        body, source = self.get(url)
        if hashlib.sha256(body).hexdigest() != proof.decode().split()[0]:
            raise ValueError("Public archive checksum mismatch")
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            entries = archive.infolist()
            if (
                len(entries) != 1
                or entries[0].filename != filename[:-4] + ".csv"
                or entries[0].file_size > 16 * 1024 * 1024
            ):
                raise ValueError("Public archive identity/size mismatch")
            rows = list(csv.reader(io.StringIO(archive.read(entries[0]).decode("utf-8-sig"))))
        matches = [row for row in rows if row and row[0].isdigit() and int(row[0]) == start]
        if len(matches) != 1:
            raise ValueError(f"Required public bar unavailable:{symbol}/{kind}/{start}")
        source = {
            **source,
            "checksum_path": proof_meta["path"],
            "checksum_sha256": proof_meta["sha256"],
        }
        return validate_bar(matches[0], start, step), source


def validate_bar(row, start, step=HOUR):
    if len(row) < 12 or int(row[0]) != start or int(row[6]) != start + step - 1:
        raise ValueError("Bar time/schema mismatch")
    values = [float(row[i]) for i in [1, 2, 3, 4, 5, 7, 9, 10]]
    o, h, low, c, v, q, b, bq = values
    if (
        not all(math.isfinite(x) for x in values)
        or min(o, h, low, c) <= 0
        or h < max(o, c, low)
        or low > min(o, c)
        or min(v, q, b, bq) < 0
        or b > v + 1e-8
        or bq > q + 1e-8
    ):
        raise ValueError("Invalid public bar price/volume bounds")
    return {
        "bar_open_ms": start,
        "open": o,
        "high": h,
        "low": low,
        "close": c,
        "volume": v,
        "quote_volume": q,
        "taker_buy_volume": b,
        "taker_buy_quote_volume": bq,
    }


def read_market(root, config, symbols):
    hourly = root / config["hourly_root"]
    daily = root / config["daily_root"]
    collections = {"trade": [], "mark": [], "funding": []}
    bindings = {}
    for symbol in sorted(symbols):
        index_path = daily / "index" / (symbol + ".json")
        index = load_json(index_path)
        bindings[str(index_path)] = sha(index_path)
        for key, binding in sorted(index["sources"].items()):
            month = key.rsplit("-", 2)[-2] + "-" + key.rsplit("-", 1)[-1][:-4]
            if not "2021-01" <= month <= "2022-12":
                continue
            kind = (
                "funding"
                if "/fundingRate/" in key
                else "mark"
                if "/markPriceKlines/" in key
                else "trade"
                if "/klines/" in key
                else None
            )
            if kind is None:
                continue
            meta_path = hourly / "index" / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            meta = load_json(meta_path)
            path = hourly / meta["relative_path"]
            if (
                sha(meta_path) != binding["index_sha256"]
                or sha(path) != binding["parquet_sha256"]
                or meta["parquet_sha256"] != binding["parquet_sha256"]
                or meta["raw_sha256"] != binding["raw_sha256"]
            ):
                raise ValueError("First-window canonical source changed:" + key)
            columns = (
                ["instrument_id", "event_timestamp_ms", "funding_rate", "funding_interval_hours"]
                if kind == "funding"
                else [
                    "instrument_id",
                    "bar_open_ms",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "quote_volume",
                    "taker_buy_volume",
                    "taker_buy_quote_volume",
                ]
            )
            part = pq.read_table(path, columns=columns).to_pandas()
            if len(part) != meta["rows"] or (len(part) and set(part.instrument_id) != {symbol}):
                raise ValueError("Canonical row/symbol mismatch:" + key)
            collections[kind].append(part)
            bindings[str(path)] = binding["parquet_sha256"]
            bindings[str(meta_path)] = binding["index_sha256"]
    market = {kind: pd.concat(parts, ignore_index=True) for kind, parts in collections.items()}
    repair = root / config["repair_run"]
    assessment = load_json(repair / "assessment.json")
    overlay = repair / "deduplicated_observations.jsonl"
    if sha(overlay) != assessment["output_hashes"][overlay.name]:
        raise ValueError("Verified repair overlay changed")
    extra = {kind: [] for kind in market}
    for line in overlay.read_text().splitlines():
        row = json.loads(line)
        t = row["timestamp_ms"]
        if row["symbol"] not in symbols or not ms("2021-01-01") <= t < ms("2023-01-01"):
            continue
        if sha(row["source"]["path"]) != row["source"]["sha256"]:
            raise ValueError("Recovered source changed")
        bindings[row["source"]["path"]] = row["source"]["sha256"]
        if row["kind"] == "funding":
            value = {
                "event_timestamp_ms": t,
                "funding_rate": row["rate"],
                "funding_interval_hours": row["funding_interval_hours"],
            }
        else:
            value = validate_bar(row["values"], t)
        extra[row["kind"]].append({"instrument_id": row["symbol"], **value})
    for kind, parts in extra.items():
        if parts:
            market[kind] = pd.concat([market[kind], pd.DataFrame(parts)], ignore_index=True)
        key = "event_timestamp_ms" if kind == "funding" else "bar_open_ms"
        if market[kind].duplicated(["instrument_id", key]).any():
            raise ValueError("Duplicate original/recovered observation:" + kind)
        market[kind] = market[kind].sort_values(["instrument_id", key]).reset_index(drop=True)
    bindings[str(overlay)] = sha(overlay)
    return market, bindings


class WindowData:
    def __init__(self, market, notices):
        self.symbols = sorted(set(market["trade"].instrument_id) | {"BTCUSDT", "ETHUSDT"})
        self.trades = {s: {} for s in self.symbols}
        self.marks = {
            s: (np.array([], dtype=np.int64), np.array([], dtype=float)) for s in self.symbols
        }
        self.funding = {s: [] for s in self.symbols}
        self.funding_meta = {s: [] for s in self.symbols}
        self.notices = notices
        self.exit_prices = {}
        for symbol, group in market["trade"].groupby("instrument_id"):
            self.trades[symbol] = {
                int(row.bar_open_ms): (float(row.close), float(row.volume), float(row.quote_volume))
                for row in group.itertuples()
            }
        for symbol, group in market["mark"].groupby("instrument_id"):
            self.marks[symbol] = (
                group.bar_open_ms.to_numpy(dtype=np.int64) + HOUR,
                group.close.to_numpy(dtype=float),
            )
        for symbol, group in market["funding"].groupby("instrument_id"):
            self.funding_meta[symbol] = [
                (
                    int(row.event_timestamp_ms),
                    float(row.funding_interval_hours)
                    if pd.notna(row.funding_interval_hours)
                    else None,
                )
                for row in group.itertuples()
            ]
            self.funding[symbol] = [
                (int(row.event_timestamp_ms), float(row.funding_rate)) for row in group.itertuples()
            ]

    def mark(self, symbol, t):
        stamps, values = self.marks[symbol]
        index = int(np.searchsorted(stamps, t, side="right")) - 1
        if (
            index < 0
            or not 0 <= t - int(stamps[index]) <= 2 * HOUR
            or not np.isfinite(values[index])
            or values[index] <= 0
        ):
            return None
        return float(values[index]), int(stamps[index])

    def vwap(self, symbol, t):
        row = self.trades[symbol].get(t)
        return row[2] / row[1] if row and row[1] > 0 and row[2] > 0 else None

    def add_bar(self, symbol, kind, row):
        t = int(row["bar_open_ms"])
        if kind == "trade":
            replacement = (
                float(row["close"]),
                float(row["volume"]),
                float(row["quote_volume"]),
            )
            existing = self.trades[symbol].get(t)
            if existing is not None and existing != replacement:
                raise ValueError("Conflicting original/recovered trade bar")
            self.trades[symbol][t] = replacement
        else:
            stamps, values = self.marks[symbol]
            if t + HOUR in stamps:
                raise ValueError("Refusing to overwrite an original mark")
            order = np.argsort(np.r_[stamps, t + HOUR])
            self.marks[symbol] = (
                np.r_[stamps, t + HOUR][order],
                np.r_[values, float(row["close"])][order],
            )

    def events(self, start, last, days):
        events = {}

        def add(symbol, t, kind, price, mark_at=None, rate=None):
            key = symbol, t
            if key in events:
                if rate is not None:
                    events[key].update(rate=rate, funding_price=price, funding_mark_at=mark_at)
                if kind == "final":
                    events[key].update(kind=kind, price=price, mark_at=None)
                return
            events[key] = {
                "symbol": symbol,
                "stamp": t,
                "kind": kind,
                "price": price,
                "mark_at": mark_at,
                "rate": rate,
                "funding_price": price if rate is not None else None,
                "funding_mark_at": mark_at if rate is not None else None,
            }

        for t in range(start, last + 1, DAY):
            for symbol in self.symbols:
                mark = self.mark(symbol, t)
                if mark:
                    add(symbol, t * 1000000, "mark", *mark)
            anchor = self.mark("BTCUSDT", t)
            if not anchor:
                raise ValueError("Missing BTC daily anchor")
            add("BTCUSDT", t * 1000000 + 100, "snapshot", anchor[0])
            if t in days:
                for symbol in self.symbols:
                    mark = self.mark(symbol, t + HOUR)
                    if mark:
                        add(symbol, (t + HOUR) * 1000000, "reference", *mark)
                    price = self.vwap(symbol, t + HOUR)
                    if price:
                        add(symbol, (t + 2 * HOUR) * 1000000, "execution", price)
                for offset, kind in [(HOUR, "decision"), (2 * HOUR, "check")]:
                    add(
                        "BTCUSDT",
                        (t + offset) * 1000000 + 100,
                        kind,
                        self.mark("BTCUSDT", t + offset)[0],
                    )
        for symbol, value in self.notices.items():
            if start <= value["effective_ms"] <= last:
                mark = self.mark(symbol, value["effective_ms"] - 1)
                add(
                    symbol,
                    value["effective_ms"] * 1000000 + 50,
                    "terminal_boundary",
                    mark[0] if mark else 1.0,
                )
        for symbol, rows in self.funding.items():
            for t, rate in rows:
                if start <= t <= last:
                    mark = self.mark(symbol, t)
                    add(
                        symbol,
                        t * 1000000,
                        "funding",
                        mark[0] if mark else 1.0,
                        mark[1] if mark else None,
                        rate,
                    )
        for symbol, value in self.notices.items():
            t = value["exit_ms"]
            if start <= t < last and symbol in self.exit_prices:
                add(symbol, t * 1000000, "final", self.exit_prices[symbol])
        final = last - HOUR
        for symbol in self.symbols:
            price = self.vwap(symbol, final - HOUR)
            if price:
                add(symbol, final * 1000000, "final", price)
        add("BTCUSDT", final * 1000000 + 100, "final_check", self.mark("BTCUSDT", final)[0])
        return [events[k] for k in sorted(events, key=lambda k: (k[1], k[0]))]
