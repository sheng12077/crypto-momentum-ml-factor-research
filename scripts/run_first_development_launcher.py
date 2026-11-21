"""One-command cached historical workflow; isolated runtime, no shell-policy changes."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["report", "verify", "all"], default="report")
    args = parser.parse_args()
    runtime = Path(tempfile.gettempdir()) / "momentum_development_005"
    python = runtime / "venv/Scripts/python.exe"
    if not python.exists():
        uv = ROOT / "data/interim/tooling/uv_windows/bin/uv.exe"
        if not uv.exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "--target",
                            str(uv.parents[1]), "uv"], check=True)
        env = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(runtime / "python"),
                   UV_CACHE_DIR=str(runtime / "cache"))
        subprocess.run([str(uv), "venv", "--python", "3.13", str(runtime / "venv")], env=env, check=True)
        subprocess.run([str(uv), "pip", "install", "--python", str(python), "-r",
                        str(ROOT / "requirements/development-windows-py313.lock")], env=env, check=True)

    def run(name):
        subprocess.run([str(python), "-u", str(ROOT / "scripts" / name)], cwd=ROOT, check=True)

    if args.stage == "all":
        run("integrate_first_development_trades.py")
        run("run_first_development.py")
    if args.stage in ("all", "verify"):
        run("render_first_development_reports.py")
        run("verify_first_development_results.py")
    run("check_first_historical_notebook.py")


if __name__ == "__main__":
    main()
