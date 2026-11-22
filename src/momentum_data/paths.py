"""Resolve local research paths independently of the working directory."""

import os
from pathlib import Path

ROOT = Path(os.environ.get("MOMENTUM_PROJECT_ROOT", Path(__file__).resolve().parents[2])).resolve()
DATA_ROOT = Path(os.environ.get("MOMENTUM_DATA_ROOT", ROOT / "data")).resolve()
LEGACY = ROOT / "research/legacy"
