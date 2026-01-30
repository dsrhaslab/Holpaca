import argparse

from experiments.main import EXPERIMENTS

ACCOUNT = # your_account_name
PARTITION =  # the_target_partition

CWD = Path(__file__).parent.resolve().absolute()
SRCDIR = CWD / ".." / ".."


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--sif",
        type=str,
        help="Path to the Holpaca SIF file",
        default=str(SRCDIR / "holpaca.sif"),
    )

    args = parser.parse_args()

    for exp_name, experiment in EXPERIMENTS.items():
        for setup_name in experiment.setups:
            run_cmd(
                f'sbatch --account={ACCOUNT} --partition={PARTITION} --wrap "singularity run --bind "/tmp,{SRCDIR}" {args.sif} python3 {SRCDIR}/benchmarks/experiments/main.py {exp_name} -s {setup_name} --slurm"'
            )


if __name__ == "__main__":
    main()
