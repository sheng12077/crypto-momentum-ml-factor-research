"""Cross-platform entry point for the frozen research-input release (no backtest)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parents[1] / "data"
INTERIM = ROOT / "data/interim/usdm_universe"
REVIEW = INTERIM / "lifecycle_review_20261117"
PILOT = INTERIM / "normalization_pilot_004_20261117"
RELEASE = SHARED / "canonical/binance_um_research/v20261117_001"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pilot", "build", "summary", "review"))
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()
    output = PILOT if args.action == "pilot" else RELEASE
    if args.action == "summary":
        for path in (REVIEW / "summary.json", PILOT / "manifest.json", RELEASE / "manifest.json"):
            print(path)
            if path.exists():
                summary = json.loads(path.read_text(encoding="utf-8"))
                if len(summary.get("errors", [])) > 5:
                    summary["error_count"] = len(summary["errors"])
                    summary["errors"] = summary["errors"][:5]
                print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
            else:
                print("not completed yet")
        return 0
    command = [
        sys.executable,
        str(
            ROOT
            / "scripts"
            / ("review_usdm_lifecycle.py" if args.action == "review" else "build_research_data.py")
        ),
        "--census-dir",
        str(INTERIM / "census_full_20261117"),
        "--audit-dir",
        str(INTERIM / "audit_20261117"),
    ]
    if args.action == "review":
        command += [
            "--facts",
            str(ROOT / "config/lifecycle_facts.json"),
            "--output-dir",
            str(REVIEW),
        ]
    else:
        command += [
            "--data-root",
            str(SHARED),
            "--download-dir",
            str(INTERIM / "download_full_20261117"),
            "--overlay-dir",
            str(SHARED / "canonical/binance_um_mark_recovery/v20261117_001_partial"),
            "--lifecycle-dir",
            str(REVIEW),
            "--output-dir",
            str(output),
            "--workers",
            str(args.workers),
        ]
        if args.action == "pilot":
            command += [
                "--symbols",
                "BTCUSDT,LITUSDT,WAVESUSDT",
                "--months",
                "2024-06,2025-01,2025-12,2026-06",
            ]
    log_path = ROOT / "reports/acquisition" / ("research_" + args.action + "_20261117.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    print("Log:", log_path, flush=True)
    with log_path.open("a", encoding="utf-8") as log:
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        ) as process:
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
