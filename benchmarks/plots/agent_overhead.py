#!/usr/bin/env python3

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
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator
from matplotlib.transforms import Bbox, TransformedBbox

# Set modern aesthetic similar to the example
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["font.size"] = 20
plt.rcParams["axes.labelsize"] = 20
plt.rcParams["xtick.labelsize"] = 20
plt.rcParams["ytick.labelsize"] = 20
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["grid.linewidth"] = 0.7
plt.rcParams["grid.alpha"] = 0.7
plt.rcParams["grid.linestyle"] = "--"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.left"] = True
plt.rcParams["axes.spines.bottom"] = True
plt.rcParams["figure.dpi"] = 200
plt.rcParams["path.simplify"] = False


# Color palette similar to the example
COLORS = ["#de8f05", "#029e73", "#0173b2", "#cc78bc"]

LINE_STYLES = {
    "tenants": "-",
    "instances": "--",
}

COLORS_SETUP = {
    "baseline": "#0173b2",
    "holpaca": "#de8f05",
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

SETUPS = ["baseline", "holpaca"]

OUTDIR = None


def getAvgThroughput(data: [str]):
    throughputs = []
    for run in data:
        if throughput := re.search(rf"Run throughput\(ops/sec\): (.*)", run):
            throughputs.append(float(throughput.group(1)))
        else:
            print("Warning: No throughput found")
    return (np.mean(throughputs), np.std(throughputs)) if throughputs else (0, 0)


def getLatenciesPercentiles(data: [str]):
    latencies = []
    for run in data:
        if latency := re.search(rf"Mean latency \(ms\):(.*)", run):
            latencies.append(float(latency.group(1)))
        else:
            print(f"Warning: No latency found")
    return (np.mean(latencies), np.std(latencies)) if latencies else (0, 0)


def plotAvgThroughputPerLatency(
    avgThroughputs: dict, avgLatencies: dict, resultsDir: str
):
    fig, axs = plt.subplots(1, len(WORKLOADS), figsize=(9, 3), sharey=True)
    fig.tight_layout()
    fig.subplots_adjust(wspace=0.15)

    for i, workload in enumerate(WORKLOADS):
        ax = axs[i]
        for setup in SETUPS:
            for setupType in SETUP_TYPES:
                xs = []
                ys = []
                for thread in THREADS:
                    case = f"{workload}_{setupType}_{thread}"
                    if case in avgThroughputs:
                        x = avgLatencies[case][setup]
                        y = avgThroughputs[case][setup]
                        xs.append(x)
                        ys.append(y)
                        ax.scatter(
                            x,
                            y,
                            color=COLORS_SETUP[setup],
                            facecolors=COLORS_SETUP[setup],
                            marker=MARKERS[thread],
                            linewidths=0.5,
                            edgecolors=COLORS_SETUP[setup],
                            zorder=3,
                        )

                ax.plot(
                    xs,
                    ys,
                    linestyle=LINE_STYLES[setupType],
                    color=COLORS_SETUP[setup],
                    zorder=1,
                )

            ax.set_title(
                workload,
                fontsize=20,
                fontweight="bold",
                fontstyle="italic",
                pad=10,
            )

        ax.grid(True, which="both", linestyle="--", linewidth=0.5)
        ax.ticklabel_format(style="plain", axis="y")
        ax.ticklabel_format(style="plain", axis="x")

    fig.text(
        0.03,
        0.5,
        "Throughput (ops/s)",
        va="center",
        ha="left",
        rotation="vertical",
        fontsize=20,
        fontweight="bold",
    )
    fig.text(
        0.5,
        -0.065,
        "Latency (ms)",
        ha="center",
        va="bottom",
        fontsize=20,
        fontweight="bold",
    )
    legends = {
        **{
            f"{setup}": Rectangle((0, 0), 1, 1, color=COLORS_SETUP[setup], label=setup)
            for setup in SETUPS
        },
        **{
            f"{setupType}": plt.Line2D(
                [0], [0], color="black", linestyle=LINE_STYLES[setupType]
            )
            for setupType in SETUP_TYPES
        },
    }
    fig.legend(
        legends.values(),
        legends.keys(),
        loc="upper left",
        ncol=2,
        bbox_to_anchor=(0.02, 0.11),
        columnspacing=0.6,
        handlelength=1,
        handleheight=1,
        handletextpad=0.4,
        fontsize=20,
    )
    legends = {
        str(thread): plt.Line2D(
            [0], [0], color="black", marker=MARKERS[thread], linestyle="None"
        )
        for thread in THREADS
    }
    fig.legend(
        legends.values(),
        legends.keys(),
        loc="upper right",
        ncol=3,
        bbox_to_anchor=(0.97, 0.11),
        handletextpad=0.02,
        columnspacing=0.1,
    )

    plt.savefig(
        OUTDIR / "avg_throughput_per_latency.png", bbox_inches="tight", pad_inches=0
    )
    plt.savefig(
        OUTDIR / "avg_throughput_per_latency.pdf", bbox_inches="tight", pad_inches=0
    )
    plt.close()


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

    for workload in WORKLOADS:
        for setupType in SETUP_TYPES:
            for thread in THREADS:
                case = f"{workload}_{setupType}_{thread}"
                avgThroughputs[case] = {}
                avgLatencies[case] = {}
                for setup in SETUPS:
                    results = []
                    for path in glob.glob(f"{setup}_{setupType}_{workload}_{thread}_*"):
                        with open(results_dir / path, "r") as f:
                            results.append(f.read())
                    avgThroughputs[case][setup] = getAvgThroughput(results)[0]
                    avgLatencies[case][setup] = getLatenciesPercentiles(results)[0]

    plotAvgThroughputPerLatency(avgThroughputs, avgLatencies, results_dir)


if __name__ == "__main__":
    main()
