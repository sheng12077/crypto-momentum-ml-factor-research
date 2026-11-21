"""Logged orchestration of the registered 2024 validation; final holdout stays sealed."""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/validation_2024/v20261121_002"
STAGES = {"prepare": "prepare_validation_2024.py", "spot": "build_validation_2024_spot.py",
          "simulate": "run_validation_2024.py", "report": "report_validation_2024.py"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["all", *STAGES, "summary"], default="all")
    args = parser.parse_args()
    if args.stage == "summary":
        path = BASE / "results/summary.json"
        if not path.exists():
            print(json.dumps({"success": False, "completed": False,
                "engine_completion_files": len(list((BASE / "results").glob("*/slippage_*/engine_summary.json"))),
                "model_saved": (BASE / "results/model/model_summary.json").exists(),
                "final_2025_2026_OOS_inspected": False}))
        else:
            summary = json.loads(path.read_text())
            verification = BASE / "results/independent_verification.json"
            print(json.dumps({"success": summary["success"],
                "registered_runs_completed": summary["registered_runs_completed"],
                "primary_replay_identical": summary["primary_replay_identical"],
                "report_verified": verification.exists(),
                "evidence_gates": summary["evidence_gates"],
                "primary_results": {name: {k: row[k] for k in ("total_return", "Sharpe_rf0", "MDD")}
                    for name, row in summary["primary_results"].items()},
                "final_2025_2026_OOS_inspected": summary["final_2025_2026_OOS_inspected"]}))
        return
    log = ROOT / "reports/acquisition" / f"frozen_2024_{args.stage}_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"Log: {log}", flush=True)
    with log.open("w", encoding="utf-8") as handle:
        for stage in (list(STAGES) if args.stage == "all" else [args.stage]):
            process = subprocess.Popen([sys.executable, "-u", str(ROOT / "scripts" / STAGES[stage])],
                                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace")
            for line in process.stdout:
                handle.write(line)
                handle.flush()
                print(line, end="", flush=True)
            if process.wait():
                failure = {"success": False, "failed_stage": stage, "exit_code": process.returncode,
                           "log": str(log), "final_2025_2026_OOS_inspected": False}
                BASE.mkdir(parents=True, exist_ok=True)
                (BASE / "last_failure.json").write_text(json.dumps(failure, indent=2)+"\n")
                raise SystemExit(process.returncode)


if __name__ == "__main__":
    main()
