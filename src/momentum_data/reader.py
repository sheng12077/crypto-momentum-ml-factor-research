"""Read observations without silently filling absent source data."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class DataUnavailableError(ValueError):
    """Requested observations or source coverage are absent."""


class ResearchData:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self._identities: dict[str, dict[str, Any]] = {
            row["instrument_id"]: row
            for row in json.loads(
                (self.root / "lifecycle/identity_ledger.json").read_text(encoding="utf-8")
            )
        }
        if not self.manifest["success"]:
            raise DataUnavailableError("data release build is incomplete")

    def lifecycle(self, symbol: str) -> dict[str, Any]:
        """Ex-post facts and unresolved items; never a point-in-time trading signal."""
        if symbol not in self._identities:
            raise DataUnavailableError("instrument absent from lifecycle review ledger")
        return self._identities[symbol]

    def _check_identity(self, symbol: str, start: datetime, end: datetime) -> None:
        identity = self.lifecycle(symbol)
        for event in identity["official_events"]:
            if event["event_type"] == "automatic_settlement":
                boundary = datetime.fromisoformat(event["effective_at"])
                if start < boundary < end:
                    raise DataUnavailableError(
                        "request crosses known automatic settlement; split episodes"
                    )
        if identity["known_identity_reuse"]:
            launches = sorted(
                datetime.fromisoformat(event["effective_at"])
                for event in identity["official_events"]
                if event["event_type"] == "launch"
            )
            if not launches:
                raise DataUnavailableError("identity reuse has no established boundary")
            # The latest supported launch separates identities. The hour containing
            # a fractional launch is itself partial; it is not a full tradable hour.
            boundary = launches[-1].replace(minute=0, second=0, microsecond=0)
            if start < boundary < end:
                raise DataUnavailableError(
                    "request crosses known underlying identity reuse; split episodes"
                )

    @staticmethod
    def _bounds(symbol: str, start: datetime, end: datetime) -> tuple[datetime, datetime]:
        if any(value in symbol for value in ("/", "\\", "..")):
            raise ValueError("unsafe instrument identifier")
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("require timezone-aware increasing bounds")
        return start.astimezone(UTC), end.astimezone(UTC)

    def _read(self, symbol: str, start: datetime, end: datetime, kind: str) -> Any:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq

        start, end = self._bounds(symbol, start, end)
        self._check_identity(symbol, start, end)
        cursor = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        tables = []
        while cursor < end:
            path = self.root / "observations" / kind / symbol / f"{cursor:%Y-%m}.parquet"
            if not path.exists():
                raise DataUnavailableError(
                    f"no {kind} partition for {symbol} {cursor:%Y-%m}; never assume zero"
                )
            tables.append(pq.read_table(path))
            cursor = (
                cursor.replace(year=cursor.year + 1, month=1)
                if cursor.month == 12
                else cursor.replace(month=cursor.month + 1)
            )
        table = pa.concat_tables(tables)
        field = "event_time" if kind == "funding" else "bar_open_time"
        mask = pc.and_(
            pc.greater_equal(table[field], pa.scalar(start, type=table[field].type)),
            pc.less(table[field], pa.scalar(end, type=table[field].type)),
        )
        return table.filter(mask)

    def bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        kind: str = "trade",
        *,
        require_complete: bool = True,
    ) -> Any:
        if kind not in ("trade", "mark"):
            raise ValueError("bars kind must be trade or mark")
        start, end = self._bounds(symbol, start, end)
        if any(v.minute or v.second or v.microsecond for v in (start, end)):
            raise ValueError("hourly reads require hour-aligned bounds")
        table = self._read(symbol, start, end, kind)
        if require_complete:
            expected, cursor = set(), start
            while cursor < end:
                expected.add(int(cursor.timestamp() * 1000))
                cursor += timedelta(hours=1)
            observed = set(table["bar_open_ms"].to_pylist())
            if len(observed) != table.num_rows or observed != expected:
                raise DataUnavailableError(
                    "hourly coverage incomplete; inspect masks, do not forward fill"
                )
        return table

    def funding(self, symbol: str, start: datetime, end: datetime) -> Any:
        """Exact source events, not forecasts or a claim of payable funding."""
        return self._read(symbol, start, end, "funding")
