import argparse
import glob
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


def printLat(controllerLatency, avgCCEs):
    for setupType in SETUP_TYPES:
        print(f"Setup Type: {setupType}")
        for thread in THREADS:
            lat = controllerLatency[setupType][thread]
            relColLat = avgCCEs[setupType][thread]["collect"] / lat * 100
            relComLat = avgCCEs[setupType][thread]["compute"] / lat * 100
            relEnfLat = avgCCEs[setupType][thread]["enforce"] / lat * 100
            print(f"{thread},{lat:.2f},{relColLat:.2f},{relComLat:.2f},{relEnfLat:.2f}")
        print("\n")


def main():
    global OUTDIR, WORKLOADS, THREADS, SETUP_TYPES, SETUPS

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "experiment_results_dir", type=str, help="Directory with experiment results"
    )

    args = parser.parse_args()

    results_dir = Path(args.experiment_results_dir).resolve().absolute()
    OUTDIR = results_dir

    avgThroughputs = {}
    avgLatencies = {}

    avgCCEs = {}
    controllerLatency = {}
    for setupType in SETUP_TYPES:
        controllerLatency[setupType] = {}
        avgCCEs[setupType] = {}
        for thread in THREADS:
            avgCCEs[setupType][thread] = {}
            collect = []
            compute = []
            enforce = []
            for workload in WORKLOADS:
                case = f"holpaca_{setupType}_{workload}_{thread}"
                avgThroughputs[case] = {}
                avgLatencies[case] = {}
                results = []
                for path in glob.glob(f"{case}_*"):
                    df = pd.read_csv(
                        results_dir / case / "orchestrator.log",
                        header=None,
                    )
                    column_means = df.mean()
                    collect.append(column_means[0])
                    compute.append(column_means[1])
                    enforce.append(column_means[2])
                df = None  # Free memory
        avgCCEs[setupType][thread]["collect"] = np.mean(collect)
        avgCCEs[setupType][thread]["compute"] = np.mean(compute)
        avgCCEs[setupType][thread]["enforce"] = np.mean(enforce)
        controllerLatency[setupType][thread] = sum(avgCCEs[setupType][thread].values())

    printLat(controllerLatency, avgCCEs)


if __name__ == "__main__":
    main()
