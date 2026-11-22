"""User-run annual evaluation; preflight both windows before any financial runs."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ["config/dynamic_2025.json", "config/dynamic_2026.json"]


def run_batch(stage="all", root=ROOT, runner=None):
    runner = runner or subprocess.run
    plan = (
        [(config, "preflight") for config in CONFIGS] + [(config, "all") for config in CONFIGS]
        if stage == "all"
        else [(config, stage) for config in CONFIGS]
    )
    status = {"success": False, "requested_stage": stage, "completed_steps": []}
    output = root / "data/processed/dynamic_final_windows/batch_status.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.write_text(json.dumps(status, indent=2) + "\n")

    save()
    for config, action in plan:
        print(f"Window batch: {config} / {action}", flush=True)
        command = [
            sys.executable,
            "-m",
            "crypto_factor_research",
            "window",
            "--config",
            config,
            "--stage",
            action,
        ]
        try:
            result = runner(command, cwd=root, check=False)
        except OSError as exc:
            status["failed_step"] = {"config": config, "stage": action, "error": str(exc)}
            save()
            return status
        step = {"config": config, "stage": action, "returncode": result.returncode}
        if result.returncode:
            if result.returncode == -9:
                step["termination"] = "SIGKILL; check kernel OOM log before retrying"
            status["failed_step"] = step
            save()
            return status
        status["completed_steps"].append(step)
        save()
    status["success"] = True
    save()
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["all", "preflight", "summary"], default="all")
    args = parser.parse_args()
    result = run_batch(args.stage)
    print(json.dumps(result), flush=True)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
