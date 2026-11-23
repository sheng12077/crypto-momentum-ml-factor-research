"""User-run annual evaluation; preflight both windows before any financial runs."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ["config/dynamic_2025.json", "config/dynamic_2026.json"]


def run_batch(stage="all", root=ROOT, runner=None, funding_assumption="strict"):
    runner = runner or subprocess.run
    if funding_assumption not in {"strict", "adjacent-mean"}:
        raise ValueError("Unknown funding assumption")
    configs = (
        CONFIGS
        if funding_assumption == "strict"
        else [
            CONFIGS[0],
            "config/dynamic_2026_mean_funding.json",
        ]
    )
    plan = (
        [(config, "preflight") for config in configs] + [(config, "all") for config in configs]
        if stage == "all"
        else [(config, stage) for config in configs]
    )
    status = {"success": False, "requested_stage": stage, "completed_steps": []}
    label = (
        "dynamic_final_windows" if funding_assumption == "strict" else "dynamic_final_windows_mean"
    )
    output = root / "data/processed" / label / "batch_status.json"
    status["funding_assumption"] = funding_assumption
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
            "window-mean" if config.endswith("2026_mean_funding.json") else "window",
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
    parser.add_argument(
        "--funding-assumption", choices=["strict", "adjacent-mean"], default="strict"
    )
    args = parser.parse_args()
    result = run_batch(args.stage, funding_assumption=args.funding_assumption)
    print(json.dumps(result), flush=True)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
