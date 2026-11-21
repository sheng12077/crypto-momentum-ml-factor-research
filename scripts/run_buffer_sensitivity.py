"""Stdlib launcher: prepare/pilot/run/report/summary; no automatic package installs."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/buffer_sensitivity/v20261121_001"


def choose_python(explicit=None):
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_file():
            raise FileNotFoundError(f"Python executable not found: {candidate}")
        return candidate
    if os.name == "nt":
        candidate = Path(tempfile.gettempdir()) / "momentum_development_005/venv/Scripts/python.exe"
    else:
        candidate = ROOT / "data/interim/runtime/nautilus313/bin/python"
    if candidate.is_file():
        return candidate
    if sys.version_info[:2] == (3, 13):
        return Path(sys.executable)
    raise RuntimeError("No existing Python3.13 trading runtime found. Pass --python PATH. No packages were installed.")


def launch(python, script, args, log):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    with log.open("a", encoding="utf-8") as stream:
        with subprocess.Popen([str(python), "-u", str(ROOT / "scripts" / script), *args], cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              encoding="utf-8", errors="replace", env=env) as process:
            try:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    stream.write(line)
                    stream.flush()
                code = process.wait()
            except KeyboardInterrupt:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                stream.write("Interrupted; completed cases remain checkpointed.\n")
                raise
    if code:
        raise subprocess.CalledProcessError(code, [str(python), script, *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["prepare", "pilot", "run", "report", "summary", "all"], default="all")
    parser.add_argument("--python", help="Existing compatible Python3.13 executable; no install/update")
    args = parser.parse_args()
    if args.stage == "summary":
        path = BASE / "results/summary.json"
        if not path.exists():
            complete = list((BASE / "results").glob("*/retain_*/slippage_*bps/_complete.json"))
            print(json.dumps({"success": False, "state": "not_complete", "completed_cases": len(complete),
                              "expected_cases": 16, "summary_path": str(path)}))
            return
        print(json.dumps(json.loads(path.read_text(encoding="utf-8"))))
        return
    python = choose_python(args.python)
    started = time.monotonic()
    log = ROOT / "reports/acquisition" / f"buffer_sensitivity_{args.stage}_{datetime.now():%Y%m%d_%H%M%S_%f}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"Log: {log}", flush=True)
    if args.stage in ("prepare", "pilot", "run", "all"):
        mode = {"all": "run"}.get(args.stage, args.stage)
        launch(python, "buffer_sensitivity_worker.py", ["--mode", mode], log)
    if args.stage == "prepare":
        launch(python, "report_buffer_sensitivity.py", ["--prepare-only"], log)
    if args.stage in ("report", "all"):
        launch(python, "report_buffer_sensitivity.py", [], log)
    print(json.dumps({"success": True, "stage": args.stage, "log": str(log),
                      "elapsed_seconds": round(time.monotonic()-started, 3),
                      "full_historical_run_requested": args.stage in ("run", "all")}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted. Re-run the same command to resume verified completed cases.", file=sys.stderr)
        sys.exit(130)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(error.returncode if isinstance(error, subprocess.CalledProcessError) else 1)
