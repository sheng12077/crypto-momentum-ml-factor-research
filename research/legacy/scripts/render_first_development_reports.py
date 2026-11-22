"""Refresh charts only; assert previously computed financial metrics are unchanged."""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from momentum_data.backtest_analysis import load_development_run, plot_development  # noqa: E402


def main():
    root = ROOT / "data/interim/first_development/v20261121_001/results_v003"
    for model, year in [("momentum_baseline", 2021), ("lightgbm_validation", 2022)]:
        for bps in (0, 2, 5, 10):
            folder = root / model / f"slippage_{bps}bps"
            daily, _ = load_development_run(folder)
            fig, metrics, _ = plot_development(daily)
            original = pd.read_csv(folder / "metrics.csv", index_col="series")
            if not np.allclose(metrics.to_numpy(), original[metrics.columns].to_numpy(),
                               rtol=0, atol=1e-10, equal_nan=True):
                raise ValueError("Chart refresh changed financial metrics")
            fig.suptitle(f"{year}–2022 CONDITIONAL DEVELOPMENT — BTC/ETH spot-price hold benchmarks")
            fig.savefig(folder / "dashboard.png", dpi=160)
            plt.close(fig)
    print("Refreshed eight charts; all financial metrics unchanged", flush=True)


if __name__ == "__main__":
    main()
