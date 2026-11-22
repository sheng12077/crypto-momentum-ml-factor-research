"""Execute the analysis notebook in this interpreter's isolated Jupyter kernel."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "notebooks/backtest_analysis.ipynb"
    notebook = nbformat.read(source, as_version=4)
    nbformat.validate(notebook)
    kernel_dir = Path(sys.prefix) / "share/jupyter/kernels"
    manager = KernelManager(
        kernel_name="python3",
        kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_dir)]),
    )
    client = NotebookClient(notebook, km=manager, timeout=120,
                            resources={"metadata": {"path": str(ROOT)}}, allow_errors=False)
    client.execute()
    target = ROOT / "reports/acquisition/backtest_analysis_executed.ipynb"
    target.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, target)
    errors = [o for c in notebook.cells if c.cell_type == "code" for o in c.outputs
              if o.output_type == "error"]
    if errors:
        raise RuntimeError("Notebook execution has error outputs")
    print(json.dumps({"success": True, "code_cells_executed": sum(
        c.cell_type == "code" for c in notebook.cells), "executed_notebook": str(target),
        "historical_strategy_performance_computed": False, "OOS_performance_inspected": False}))


if __name__ == "__main__":
    main()
