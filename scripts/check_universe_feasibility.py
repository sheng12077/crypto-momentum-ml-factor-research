"""Metadata-only Binance universe feasibility; never reads strategy returns or ZIPs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
ROOTS = {
    "trade": "data/futures/um/monthly/klines/",
    "mark": "data/futures/um/monthly/markPriceKlines/",
    "funding": "data/futures/um/monthly/fundingRate/",
    "spot": "data/spot/monthly/klines/",
}
PILOT = ("BTCUSDT", "ETHUSDT", "LUNAUSDT", "LUNCUSDT", "FTTUSDT", "WAVESUSDT")


def parse_listing(body: bytes) -> tuple[list[str], list[dict], str | None]:
    root = ET.fromstring(body)
    if root.tag.rsplit("}", 1)[-1] != "ListBucketResult":
        raise ValueError("response is not a ListBucketResult")
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    prefixes = [n.text for n in root.findall("s:CommonPrefixes/s:Prefix", ns) if n.text]
    objects = [
        {
            "key": n.findtext("s:Key", namespaces=ns),
            "size": int(n.findtext("s:Size", default="0", namespaces=ns)),
        }
        for n in root.findall("s:Contents", ns)
    ]
    truncated = root.findtext("s:IsTruncated", namespaces=ns)
    if truncated not in ("true", "false"):
        raise ValueError("missing or invalid IsTruncated")
    token = root.findtext("s:NextContinuationToken", namespaces=ns)
    if truncated == "true" and not token:
        raise ValueError("truncated listing lacks continuation token")
    return prefixes, objects, token if truncated == "true" else None


def month_range(start: str, end: str) -> list[str]:
    year, month = map(int, start.split("-"))
    result = []
    while (label := f"{year:04d}-{month:02d}") <= end:
        result.append(label)
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return result


def summarize_files(symbol: str, kind: str, objects: list[dict]) -> dict:
    name = "fundingRate" if kind == "funding" else "1h"
    pattern = re.compile(rf"{re.escape(symbol)}-{name}-(\d{{4}}-\d{{2}})\.zip")
    keys = {obj["key"] for obj in objects}
    files = []
    for obj in objects:
        match = pattern.fullmatch(obj["key"].rsplit("/", 1)[-1])
        if match and "2021-01" <= match[1] <= "2026-10":
            files.append(
                {**obj, "month": match[1], "has_checksum": obj["key"] + ".CHECKSUM" in keys}
            )
    files.sort(key=lambda row: row["month"])
    months = sorted({row["month"] for row in files})
    return {
        "months": months,
        "first_month": months[0] if months else None,
        "last_month": months[-1] if months else None,
        "missing_interior_months": sorted(set(month_range(months[0], months[-1])) - set(months))
        if months
        else [],
        "checksum_gaps": [row["month"] for row in files if not row["has_checksum"]],
        "zip_count": len(files),
        "zip_bytes": sum(row["size"] for row in files),
        "files": files,
    }


class Discovery:
    def __init__(self, output: Path):
        self.output = output
        (output / "responses").mkdir(parents=True, exist_ok=False)
        self.manifest: list[dict] = []

    def get(self, label: str, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": "universe-feasibility/0.1"})
        with urllib.request.urlopen(request, timeout=40) as response:
            body = response.read()
            status = response.status
        relative = f"responses/{label}.raw"
        (self.output / relative).write_bytes(body)
        self.manifest.append(
            {
                "source_url": url,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "status": status,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "path": relative,
            }
        )
        return body

    def listing(self, label: str, prefix: str, delimiter: str | None = None) -> tuple[list, list]:
        prefixes, objects, seen = [], [], set()
        token = None
        for page in range(1000):
            params = {"list-type": "2", "prefix": prefix}
            if delimiter:
                params["delimiter"] = delimiter
            if token:
                params["continuation-token"] = token
            body = self.get(f"{label}_{page:03d}", S3 + "?" + urllib.parse.urlencode(params))
            found, rows, token = parse_listing(body)
            prefixes.extend(found)
            objects.extend(rows)
            if token is None:
                return sorted(set(prefixes)), objects
            if token in seen:
                raise ValueError("pagination token cycle")
            seen.add(token)
        raise ValueError("pagination exceeded 1000-page safety bound")


def run(output: Path) -> dict:
    client = Discovery(output)
    result: dict = {
        "window": ["2021-01", "2026-10"],
        "roots": {},
        "pilot": {},
        "errors": [],
        "current_inventory": None,
    }
    for kind, prefix in ROOTS.items():
        try:
            prefixes, _ = client.listing(f"root_{kind}", prefix, "/")
            symbols = sorted(p.rstrip("/").rsplit("/", 1)[-1] for p in prefixes)
            usdt = [s for s in symbols if re.fullmatch(r"[A-Z0-9]+USDT", s)]
            result["roots"][kind] = {
                "all_symbols": symbols,
                "usdt_symbols": usdt,
                "all_count": len(symbols),
                "usdt_count": len(usdt),
            }
            print(
                f"root {kind}: {len(symbols)} directories, {len(usdt)} USDT candidates", flush=True
            )
        except Exception as exc:
            result["errors"].append({"stage": f"root_{kind}", "error": str(exc)})
    try:
        snapshot = json.loads(
            client.get("exchange_info", "https://fapi.binance.com/fapi/v1/exchangeInfo")
        )
        symbols = snapshot["symbols"]
        current = [
            s
            for s in symbols
            if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
        ]
        result["current_inventory"] = {
            "perpetual_usdt_count": len(current),
            "symbols": sorted(s["symbol"] for s in current),
            "warning": "current snapshot, not historical membership",
        }
    except Exception as exc:
        result["errors"].append({"stage": "current_inventory", "error": str(exc)})
    for symbol in PILOT:
        summaries = {}
        for kind, root in ROOTS.items():
            prefix = root + symbol + "/" + ("" if kind == "funding" else "1h/")
            try:
                _, objects = client.listing(f"pilot_{symbol}_{kind}", prefix)
                summaries[kind] = summarize_files(symbol, kind, objects)
            except Exception as exc:
                result["errors"].append({"stage": f"pilot_{symbol}_{kind}", "error": str(exc)})
        required = ("trade", "mark", "funding")
        sets = [set(summaries.get(k, {}).get("months", [])) for k in required]
        common = sorted(set.intersection(*sets))
        checksums = all(
            k in summaries and summaries[k]["zip_count"] > 0 and not summaries[k]["checksum_gaps"]
            for k in required
        )
        last = summaries.get("trade", {}).get("last_month")
        result["pilot"][symbol] = {
            "series": summaries,
            "common_required_months": common,
            "required_checksums_complete": checksums,
            "archive_ended_before_window_end": bool(last and last < "2026-10"),
        }
        print(f"pilot {symbol}: {len(common)} common months; last trade archive={last}", flush=True)
    lifecycle = [
        s
        for s, p in result["pilot"].items()
        if s not in PILOT[:2]
        and p["common_required_months"]
        and p["required_checksums_complete"]
        and p["archive_ended_before_window_end"]
    ]
    root_ok = len(result["roots"]) == 4 and not any(
        e["stage"].startswith("root_") for e in result["errors"]
    )
    controls_ok = all(
        result["pilot"][s]["common_required_months"]
        and result["pilot"][s]["required_checksums_complete"]
        for s in PILOT[:2]
    )
    result["decision"] = {
        "root_discovery_passed": root_ok,
        "controls_passed": controls_ok,
        "archive_ended_pilot_symbols": lifecycle,
        "lifecycle_recovery_provisional": len(lifecycle) >= 2,
        "proceed_to_coverage_census_and_row_pilot": root_ok and controls_ok and len(lifecycle) >= 2,
        "full_download_ready": False,
        "complete_historical_universe_proven": False,
    }
    result["metadata_requests"] = len(client.manifest)
    result["metadata_bytes"] = sum(r["bytes"] for r in client.manifest)
    result["market_zip_downloads"] = 0
    for name, data in (("manifest.json", client.manifest), ("summary.json", result)):
        (output / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["decision"], sort_keys=True), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
