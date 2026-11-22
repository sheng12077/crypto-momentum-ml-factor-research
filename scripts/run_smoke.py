"""Thin source-checkout entry point; implementation lives in momentum_data."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

if __name__ == "__main__":
    from momentum_data.cli import execute

    execute("smoke")
