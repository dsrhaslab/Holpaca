import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MaxNLocator

# Set modern aesthetic similar to the example
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["font.size"] = 14
plt.rcParams["axes.labelsize"] = 14
plt.rcParams["xtick.labelsize"] = 12
plt.rcParams["ytick.labelsize"] = 12
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["grid.linewidth"] = 0.7
plt.rcParams["grid.alpha"] = 0.7
plt.rcParams["grid.linestyle"] = "--"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.left"] = True
plt.rcParams["axes.spines.bottom"] = True
plt.rcParams["figure.dpi"] = 200

# Color palette similar to the example
COLORS = ["#de8f05", "#029e73", "#0173b2", "#cc78bc"]

LINE_STYLES = {
    "tenants": "-",
    "instances": "--",
}

MARKERS = {
    1: "*",
    2: "o",
    4: "s",
    8: "^",
    16: "D",
    32: "p",
}

WORKLOADS = ["read-only", "mixed", "write-heavy"]

THREADS = [1, 2, 4, 8, 16, 32]

SETUP_TYPES = ["tenants", "instances"]

FREQS = [1, 10, 100, 1000, 10000]


def main():
    global OUTDIR, WORKLOADS, THREADS, SETUP_TYPES, SETUPS

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "experiment_results_dir", type=str, help="Directory with experiment results"
    )

    args = parser.parse_args()

    results_dir = Path(args.experiment_results_dir).resolve().absolute()

    for setupType in SETUP_TYPES:
        for thread in THREADS:
            for freq in FREQS:
                for workload in WORKLOADS:
                    case = f"holpaca_{setupType}_{workload}_{freq}_{thread}"
                    df = pd.read_csv(
                        results_dir / case / "dool.csv",
                        header=None,
                    )
                    cpu.append(df["usr"].mean())
                print(f"[{setupType}][{thread}][{freq}]: {np.mean(cpu)}")


if __name__ == "__main__":
    main()
