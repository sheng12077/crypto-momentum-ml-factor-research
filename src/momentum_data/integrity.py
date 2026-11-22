"""Immutable artifact verification and historical source-path resolution."""

import hashlib
import json
import math
from importlib.metadata import version
import numpy as np
from .paths import ROOT, DATA_ROOT, LEGACY


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)

    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(v) for v in value]
        if isinstance(value, np.generic):
            value = value.item()
        return None if isinstance(value, float) and not math.isfinite(value) else value

    path.write_text(
        json.dumps(clean(obj), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def bind(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f"Immutable contract mismatch: {path}; do not delete contracts")
    else:
        write(path, value)


def checked_manifest(folder, filename="manifest.json"):
    obj = json.loads((folder / filename).read_text())
    if any(sha(folder / n) != h for n, h in obj["output_hashes"].items()):
        raise ValueError(f"Changed outputs in {folder}")
    return obj


def frozen_path(relative):
    """Keep original logical contract keys; resolve preserved source bytes after relocation."""
    if relative.startswith(("scripts/", "src/", "experiments/")):
        return LEGACY / relative
    if relative.startswith("data/"):
        return DATA_ROOT / relative[5:]
    return ROOT / relative


def verify_frozen_contract(base):
    meta = json.loads((base / "contract.json").read_text())
    for name, digest in meta["hashes"].items():
        if sha(frozen_path(name)) != digest:
            raise ValueError(f"Frozen source/input changed: {name}")
    for package, expected in meta["runtime"].items():
        if version(package) != expected:
            raise ValueError(f"Frozen runtime mismatch: {package}")
    return meta


def package_contract():
    files = sorted((ROOT / "src/momentum_data").rglob("*.py")) + [ROOT / "config/continuous.json"]
    return {
        "hashes": {str(p.relative_to(ROOT)): sha(p) for p in files},
        "runtime": {
            p: version(p) for p in ("nautilus_trader", "lightgbm", "numpy", "pandas", "pyarrow")
        },
    }
