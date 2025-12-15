import argparse
from pathlib import Path

import agent_overhead
import motivation_1
import motivation_2
import orchestrator_algorithm_latency_breakdown
import orchestrator_control_interval
import use_case_1
import use_case_2
import use_case_3

EXPERIMENTS = {
    "use_case_1": use_case_1.EXPERIMENT,
    "use_case_2": use_case_2.EXPERIMENT,
    "use_case_3": use_case_3.EXPERIMENT,
    "motivation_1": motivation_1.EXPERIMENT,
    "motivation_2": motivation_2.EXPERIMENT,
    "agent_overhead": agent_overhead.EXPERIMENT,
    "orchestrator_algorithm_latency_breakdown": orchestrator_algorithm_latency_breakdown.EXPERIMENT,
    "orchestrator_control_interval": orchestrator_control_interval.EXPERIMENT,
}

CWD = Path(__file__).resolve().parent.absolute()
SRCDIR = CWD / ".." / ".."


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-o",
        "--outdir",
        type=str,
        help="Path to the directory for the results",
        default=str(SRCDIR / "benchmarks" / "results"),
    )

    parser.add_argument(
        "-i",
        "--install-prefix",
        type=str,
        help="Path to the Holpaca installation directory",
        default=str(SRCDIR / "opt" / "holpaca"),
    )

    parser.add_argument("experiment_name", type=str, help="Experiment name")

    parser.add_argument(
        "-s", "--setup", type=str, help="Run only the specified setup", default=None
    )

    parser.add_argument(
        "-m",
        "--max-exec-time",
        type=int,
        help="Override configured timeout in seconds",
        default=None,
    )
    parser.add_argument(
        "-c",
        "--cache-size",
        type=int,
        help="Override configured cache size per thread",
        default=None,
    )
    parser.add_argument(
        "-l",
        "--objsize",
        type=int,
        help="Override object size (or length) in bytes",
        default=None,
    )
    parser.add_argument(
        "-n", "--num-ops", type=int, help="Override number of operations", default=None
    )
    parser.add_argument(
        "-t",
        "--tracesdir",
        type=str,
        help="Traces directory",
        default=str(SRCDIR / "benchmarks" / "twitter_traces"),
    )

    parser.add_argument("--slurm", action="store_true", help="Using SLURM scheduler")

    args = parser.parse_args()

    if not args.experiment_name in EXPERIMENTS:
        raise ValueError(f"Experiment '{args.experiment_name}  not found")

    experiment = EXPERIMENTS[args.experiment_name]

    if args.max_exec_time is not None:
        print(f"Overriding max execution time to {args.max_exec_time}")
        experiment.set_timeout(args.max_exec_time)

    if args.objsize is not None:
        print(f"Overriding object size to {args.objsize}")
        experiment.set_objsize(args.objsize)

    if args.num_ops is not None:
        print(f"Overriding number of operations to {args.num_ops}")
        experiment.set_num_ops(args.num_ops)

    if args.cache_size is not None:
        print(f"Overriding cache size per thread to {args.cache_size}")
        experiment.set_cache_size(args.cache_size)

    if args.setup is not None and args.setup not in experiment.setups:
        raise ValueError(
            f"Setup '{args.setup}' not found in experiment '{args.experiment_name}'"
        )

    experiment.run(
        Path(args.outdir),
        Path(args.install_prefix) / "bin",
        only_setup=args.setup,
        using_slurm=args.slurm,
        tracesdir=Path(args.tracesdir),
    )


if __name__ == "__main__":
    main()
