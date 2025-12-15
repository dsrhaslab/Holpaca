import argparse
import colorsys
import json
import math
import os
import re
import sys
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

# Set modern aesthetic similar to the example
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["font.size"] = 16
plt.rcParams["axes.labelsize"] = 16
plt.rcParams["xtick.labelsize"] = 14
plt.rcParams["ytick.labelsize"] = 14
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

OUTDIR = None
THREADS = 4
SETUPS = {"baseline": {}, "custom": {}, "optimizer": {}}
DIST_NAMES = {}
THREAD_NAMES = [f"T$_{i+1}$" for i in range(THREADS)]


# Color palette similar to the example
LINE_COLORS = ["#de8f05", "#029e73", "#0173b2", "#c360b0"]
COLORS = ["#fef0d8", "#cffef1", "#d1eeff", "#f7e8f4"]
STRIPE_COLORS = ["#eec783", "#64ebc6", "#69c0ef", "#e0add6"]


def getThroughput(results: str):
    values = [[] for _ in range(THREADS)]
    for i in range(THREADS):
        throughput = []
        if t := re.findall(rf"\[T-{i}\]: (\d+)", results):
            throughput = [int(x) for x in t]
        else:
            RaiseError(f"No throughput data found for thread {i}")
        # From cumulative to per-second
        previousThroughput = 0
        for t in throughput:
            t = t - previousThroughput
            values[i].append(t)
            previousThroughput += t

    return values


def getMemory(results: str):
    values = [[] for _ in range(THREADS)]
    for i in range(THREADS):
        if m := re.findall(rf"\[T-{i}\]:.*\(.*?\/ (\d+)", results):
            values[i] = [int(x) for x in m]
        else:
            RaiseError(f"No memory data found for thread {i}")

    return values


def getUsedMemory(results: str):
    values = [[] for _ in range(THREADS)]
    for i in range(THREADS):
        if m := re.findall(rf"\[T-{i}\]:.*\(.*: (\d+)", results):
            values[i] = [int(x) for x in m]
        else:
            RaiseError(f"No used memory data found for thread {i}")
    return values


def plot(
    throughput_per_setup: dict,
    memory_capacity_per_setup: dict,
    memory_used_per_setup: dict,
):

    n_cols = len(SETUPS)
    fig = plt.figure(figsize=(16, 5))
    gs = GridSpec(4, n_cols, figure=fig)

    # Create axes for the first 4 rows (standard grid)
    axs = []
    for r in range(4):
        row_axes = []
        for c in range(n_cols):
            ax = fig.add_subplot(gs[r, c])
            row_axes.append(ax)
        axs.append(row_axes)

    axs = np.array(axs)

    fig.tight_layout(pad=5)

    # Find max value per thread
    max_time = max(
        len(throughput_per_setup[setup][0]) for setup in throughput_per_setup
    )
    max_values = [0 for _ in range(THREADS)]
    max_memory_values = [0 for _ in range(THREADS)]
    for i in range(THREADS):
        for setup, throughput_values in throughput_per_setup.items():
            max_values[i] = max(max_values[i], max(throughput_values[i]))
            max_memory_values[i] = max(
                max_memory_values[i], max(memory_capacity_per_setup[setup][i])
            )

    time = np.arange(max_time)

    for i, (setup, metrics) in enumerate(throughput_per_setup.items()):
        for j, values in enumerate(metrics):
            print(f"[{setup}][{THREAD_NAMES[j]}] Max throughput: {max(values)}")
            print(f"[{setup}][{THREAD_NAMES[j]}] Avg throughput: {np.mean(values)}")
            print(
                f"[{setup}][{THREAD_NAMES[j]}] Max memory: {max(memory_capacity_per_setup[setup][j])}"
            )
            print(
                f"[{setup}][{THREAD_NAMES[j]}] Max used memory: {max(memory_used_per_setup[setup][j])}"
            )

            # If time series is shorter than max_time, pad with zeros
            values[len(values) : max_time] = [0] * (max_time - len(values))

            axs[j, i].set_xlim(0, time[-1])
            axs[j, i].set_ylim(0, max_values[j])
            # Hide the left spine for all but the leftmost columns
            if i > 0:
                axs[j, i].spines["left"].set_visible(False)
                axs[j, i].set_yticklabels([])
            # Hide the right spine for all but the rightmost columns
            if i < len(SETUPS) - 1:
                axs[j, i].spines["right"].set_visible(False)
            # Hide the top spine for all but the topmost rows
            if j > 0:
                axs[j, i].spines["top"].set_visible(False)

            # Hide the bottom spine for all but the bottommost rows
            if j < THREADS - 1:
                axs[j, i].spines["bottom"].set_visible(False)

            # Setup name on the bottom of each column
            if j == 0:
                axs[j, i].xaxis.set_label_position("top")

            axs[j, i].set_yticks(np.linspace(0, max_values[j] + 1e-9, 4))
            axs[j, i].tick_params(axis="y", pad=10)

            # Workload name on the left of each row
            # Memory
            ax2 = axs[j, i].twinx()
            ax2.ticklabel_format(style="plain", axis="y")
            axs[j, i].set_zorder(ax2.get_zorder() + 1)
            axs[j, i].patch.set_visible(False)
            # Used memory and on top, with stripes, the diff between used and max capacity
            used_memory_values = memory_used_per_setup[setup][j]
            used_memory_values[len(used_memory_values) : max_time] = [0] * (
                max_time - len(used_memory_values)
            )
            memory_values = memory_capacity_per_setup[setup][j]
            memory_values[len(memory_values) : max_time] = [0] * (
                max_time - len(memory_values)
            )
            capped_used_memory_values = [
                u if u < m else m for u, m in zip(used_memory_values, memory_values)
            ]
            plt.rcParams["hatch.linewidth"] = 4
            ax2.fill_between(
                time,
                memory_values,
                where=[u <= m for m, u in zip(memory_values, used_memory_values)],
                color=COLORS[j % len(COLORS)],
            )
            ax2.plot(
                time,
                used_memory_values,
                color=STRIPE_COLORS[j % len(STRIPE_COLORS)],
                linewidth=0.5,
            )
            ax2.fill_between(
                time,
                capped_used_memory_values,
                color="none",
                alpha=1,
                hatch="//",
                edgecolor=STRIPE_COLORS[j % len(STRIPE_COLORS)],
                linewidth=0,
            )
            # Wrongly used memory
            ax2.fill_between(
                time,
                memory_values,
                used_memory_values,
                where=[u > m for m, u in zip(memory_values, used_memory_values)],
                color="none",
                alpha=1,
                hatch="//",
                edgecolor="red",
                linewidth=0,
            )
            ax2.set_axisbelow(True)
            # plot main
            axs[j, i].plot(time, values, color=LINE_COLORS[j % len(COLORS)])
            ax2.set_ylim(0, max_memory_values[j])
            ax2.set_xlim(0, time[-1])
            # Hide the left spine of ax2 for all but the leftmost columns
            if i > 0:
                ax2.spines["left"].set_visible(False)
                ax2.tick_params(axis="y", pad=10)
            # Hide the right spine of ax2 for all but the rightmost columns
            if i < len(SETUPS) - 1:
                ax2.spines["right"].set_visible(False)
                ax2.set_yticklabels([])
            # Hide the top spine of ax2 for all but the topmost rows
            if j > 0:
                ax2.spines["top"].set_visible(False)

            # Hide the bottom spine of ax2 for all but the bottommost rows
            if j < THREADS - 1:
                ax2.spines["bottom"].set_visible(False)
                ax2.set_xticklabels([])

            # force 7 ticks on both y-axis
            ax2.set_yticks(np.linspace(0, max_memory_values[j] + 1e-9, 4))
            # plot a red dashed line at y=qos for the current thread if qos is defined

    fig.text(
        -0.01,
        0.5,
        f"Throughput (Ops/s)",
        va="center",
        rotation="vertical",
        fontweight="bold",
    )
    fig.text(
        1,
        0.5,
        f"Memory (B)",
        va="center",
        rotation=270,
        fontweight="bold",
    )
    fig.text(0.5, -0.0125, "Time (s)", ha="center", fontweight="bold")
    for i, (setup, metrics) in enumerate(throughput_per_setup.items()):
        axs[0, i].text(
            0.5,
            1.2,
            setup,
            transform=axs[0, i].transAxes,
            va="center",
            ha="center",
            fontsize=18,
            fontweight="bold",
            fontstyle="italic",
        )
        for j in range(THREADS):
            axs[j, i].text(
                0.01,
                1,
                THREAD_NAMES[j],
                transform=axs[j, i].transAxes,
                va="bottom",
                ha="left",
                fontsize=16,
                fontweight="bold",
            )
            axs[j, i].text(
                0.99,
                1,
                DIST_NAMES[f"{setup}_T{j}"],
                transform=axs[j, i].transAxes,
                va="bottom",
                ha="right",
                fontsize=16,
            )
    # Combine both lines and the patch
    by_label = {
        "Throughput": plt.Line2D([0], [0], color="black", lw=2),
    }
    fig.legend(
        by_label.values(),
        by_label.keys(),
        fontsize=17,
        loc="lower left",  # Place it at the bottom
        bbox_to_anchor=(0.027, -0.055),  # Centered and below the plot
        ncol=4,
    )  # Number of columns to display horizontally fancybox=True, shadow=True)

    by_label = {
        "Used Memory": Patch(
            facecolor="gray",
            alpha=1,
            hatch="//",
            label="Used Memory",
            edgecolor="#e6e6e6",
        ),
        "Memory Capacity": Patch(facecolor="#e6e6e6", label="Max Memory"),
    }
    fig.legend(
        by_label.values(),
        by_label.keys(),
        fontsize=17,
        loc="lower right",  # Place it at the bottom
        bbox_to_anchor=(0.973, -0.055),  # Centered and below the plot
        ncol=4,
    )  # Number of columns to display horizontally fancybox=True, shadow=True)

    plt.tight_layout(h_pad=0.2, w_pad=1)
    plt.savefig(
        OUTDIR / "throughput_and_memory.png",
        bbox_inches="tight",
        pad_inches=0,
    )
    plt.savefig(
        OUTDIR / "throughput_and_memory.pdf",
        bbox_inches="tight",
        pad_inches=0,
    )
    plt.close()


def main():
    global OUTDIR, DIST_NAMES, SETUPS, THREADS

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "experiment_results_dir", type=str, help="Directory with experiment results"
    )

    args = parser.parse_args()

    results_dir = Path(args.experiment_results_dir).resolve().absolute()
    OUTDIR = results_dir

    metrics = {
        "Throughput": getThroughput,
        "Memory": getMemory,
        "Used Memory": getUsedMemory,
    }

    for setup in SETUPS:
        with open(results_dir / setup / "setup.json", "r") as f:
            SETUPS[setup] = json.load(f)
            for i in range(THREADS):
                if rd := SETUPS[setup].get(
                    f"requestdistribution.{i}",
                    SETUPS[setup].get("requestdistribution", None),
                ):
                    if rd == "zipfian":
                        if zc := SETUPS[setup].get(
                            f"zipfian_const.{i}",
                            SETUPS[setup].get("zipfian_const", None),
                        ):
                            DIST_NAMES[f"{setup}_T{i}"] = f"Zipf ({zc})"
                        else:
                            DIST_NAMES[f"{setup}_T{i}"] = "Zipf (?)"
                    elif rd == "uniform":
                        DIST_NAMES[f"{setup}_T{i}"] = "Uniform"
                    else:
                        RaiseError(f"Unknown request distribution '{rd}'")
                else:
                    RaiseError("No request distribution found")

    throughput_per_setup = {}
    memory_capacity_per_setup = {}
    memory_used_per_setup = {}
    for setup in SETUPS:
        with open(results_dir / setup / "run.txt", "r") as f:
            lines = f.read()
            throughput_per_setup[setup] = getThroughput(lines)
            memory_capacity_per_setup[setup] = getMemory(lines)
            memory_used_per_setup[setup] = getUsedMemory(lines)

    plot(
        throughput_per_setup,
        memory_capacity_per_setup,
        memory_used_per_setup,
    )


if __name__ == "__main__":
    main()
