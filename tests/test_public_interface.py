import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import momentum_data
from momentum_data import demo
from momentum_data.paths import ROOT


def test_synthetic_example_without_market_data(capsys):
    result = demo.smoke()
    assert result["success"] and not result["market_data_required"]
    assert result["ending_nav"] == 109874.0


def test_core_imports_without_legacy_scripts_on_path():
    # Check a fresh interpreter, even when historical tests were collected in this process.
    code = """
import importlib, sys
for name in ('data.preflight','features.factors','models.annual','portfolio.ranking','backtest.engine','reporting.publication'):
    importlib.import_module('momentum_data.'+name)
assert not any('/research/legacy/scripts/' in str(getattr(m,'__file__','')) for m in sys.modules.copy().values())
"""
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_help_from_outside_repository(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    completed = subprocess.run(
        [sys.executable, "-m", "momentum_data", "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "replay" in completed.stdout and "smoke" in completed.stdout
