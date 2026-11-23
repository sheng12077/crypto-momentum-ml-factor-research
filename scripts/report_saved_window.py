"""Audit and report a saved window; never prepare, fit or simulate."""

import argparse
from pathlib import Path

from crypto_factor_research.config import load_json, sha
from crypto_factor_research.first_window import checked
from crypto_factor_research.window_report import report

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--allow-failed-random-controls", action="store_true")
    args = parser.parse_args()
    config_path = (ROOT / args.config).resolve()
    path = (ROOT / args.run_dir).resolve()
    manifest = checked(path)
    if manifest["identity"]["config_sha256"] != sha(config_path):
        raise ValueError("Saved run/config mismatch")
    checked(path, "preflight.json")
    report(
        ROOT,
        load_json(config_path),
        path,
        allow_failed_random_controls=args.allow_failed_random_controls,
    )


if __name__ == "__main__":
    main()
