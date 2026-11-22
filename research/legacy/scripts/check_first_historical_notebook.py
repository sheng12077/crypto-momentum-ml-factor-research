"""Execute the English historical-results notebook without fitting or trading."""

import json
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    notebook = nbformat.read(ROOT / "notebooks/first_historical_results.ipynb", as_version=4)
    nbformat.validate(notebook)
    manager = KernelManager(kernel_name="python3", kernel_spec_manager=KernelSpecManager(
        kernel_dirs=[str(Path(sys.prefix) / "share/jupyter/kernels")]))
    client = NotebookClient(notebook, km=manager, timeout=180, allow_errors=False,
                            resources={"metadata": {"path": str(ROOT)}})
    client.execute()
    output = ROOT / "reports/acquisition/first_historical_results_executed.ipynb"
    nbformat.write(notebook, output)
    print(json.dumps({"success": True, "notebook": str(output),
                      "code_cells_executed": sum(c.cell_type == "code" for c in notebook.cells),
                      "model_refitted": False, "OOS_performance_inspected": False}))


if __name__ == "__main__":
    main()
