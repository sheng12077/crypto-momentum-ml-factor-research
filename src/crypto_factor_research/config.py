"""Explicit input configuration; no hidden project-root or population switches."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

HOUR = 3_600_000
DAY = 24 * HOUR


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


@dataclass(frozen=True)
class InputSpec:
    root: Path
    values: dict

    @classmethod
    def read(cls, path, root):
        values = load_json(path)
        required = {
            "daily_root",
            "hourly_root",
            "source_start",
            "source_stop",
            "decision_start",
            "decision_stop",
            "funding_lag_hours",
            "funding_window_days",
            "history_days",
            "output_root",
        }
        if not required <= set(values):
            raise ValueError("Missing full-universe configuration fields")
        if (
            values["history_days"] != 120
            or values["funding_lag_hours"] != 1
            or values["funding_window_days"] != 7
        ):
            raise ValueError("Configuration differs from registered017input definitions")
        return cls(Path(root).resolve(), values)

    def path(self, key):
        return self.root / self.values[key]

    def identity_values(self):
        return {k: v for k, v in self.values.items() if k != "output_root"}
