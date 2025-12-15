import json
import os
import subprocess
from pathlib import Path

from utils.setup import Setup

EXECUTABLE = "YCSB-cpp"
ORCHESTRATOR = "holpaca_orchestrator"


def run_cmd(cmd, cwd=None):
    """Run command and exit on failure."""
    print(f"Running: {cmd}")
    subprocess.run(cmd, cwd=cwd, check=True, shell=True)


def run_slurm(bindir, setup, outdir, status, tracesdir=None):
    tmpdir = Path("/tmp")
    # Copy executable files to /tmp to avoid i/o interference
    run_cmd(f"cp {bindir}/{{{EXECUTABLE},{ORCHESTRATOR}}} {tmpdir}")
    orchestrator_exe = tmpdir / ORCHESTRATOR
    ycsb_exe = tmpdir / EXECUTABLE
    setup.config["rocksdb.dbname"] = str(tmpdir / ".db")
    setup.config["loadoutputfile"] = str(tmpdir / "load.txt")
    setup.config["runoutputfile"] = str(tmpdir / "run.txt")
    # Copy traces if needed
    if setup.config.get("workload.type", "") == "trace":
        if tracesdir is None:
            raise ValueError("Traces directory must be specified for trace workloads")
        run_cmd(f"cp {tracesdir}/cluster* {tmpdir}/")
        setup.config["trace.dir"] = str(tmpdir)
    # Get total CPU cores
    total_cores = os.cpu_count()

    # Assign cores: dool (core 0), setup (core 1), orchestrator (cores 2+)
    dool_cores = "0"
    setup_cores = "1"
    orchestrator_cores = f"2-{total_cores - 1}" if total_cores > 2 else "2"

    # If orchestrator is specified, start it before the agent
    if setup.orchestrator_address:
        # Start orchestrator
        orchestrator_output = open(tmpdir / "orchestrator.log", "w")
        if not orchestrator_output:
            print(f"Error opening orchestrator log file in {tmpdir}")
            exit(1)
        orchestrator = subprocess.Popen(
            [
                "taskset",
                "-c",
                orchestrator_cores,
                orchestrator_exe,
                setup.orchestrator_address,
                *setup.orchestrator_args,
            ],
            stdout=orchestrator_output,
        )
    # Start dool
    try:
        dool = subprocess.Popen(
            [
                "taskset",
                "-c",
                dool_cores,
                "dool",
                "-cdlmnyt",
                "--output",
                f"{tmpdir / 'dool.csv'}",
            ],
            stdout=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"Error starting dool: {e}")
        exit(1)
    # Start run
    setup_cmd = setup.cmd(ycsb_exe, status=status)
    print(f"Executing: {setup_cmd}")
    subprocess.run(
        f"taskset -c {setup_cores} {setup_cmd}",
        shell=True,
    )
    dool.terminate()
    # Terminate orchestrator and dool
    if setup.orchestrator_address:
        orchestrator.terminate()
        run_cmd(f"cp {tmpdir}/orchestrator.log {outdir}/")
    run_cmd(f"cp {tmpdir}/{{load.txt,run.txt,dool.csv}} {outdir}/")
    with open(outdir / "setup.json", "w") as f:
        f.write(json.dumps(setup.config, indent=2))


def run(bindir, setup, outdir, status, tracesdir=None):
    orchestrator_exe = bindir / ORCHESTRATOR
    ycsb_exe = bindir / EXECUTABLE
    setup.config["rocksdb.dbname"] = str(outdir / ".db")
    setup.config["loadoutputfile"] = str(outdir / "load.txt")
    setup.config["runoutputfile"] = str(outdir / "run.txt")
    if setup.config.get("workload.type", "") == "trace":
        if tracesdir is None:
            raise ValueError("Traces directory must be specified for trace workloads")
        setup.config["trace.dir"] = str(tracesdir)
    # If orchestrator is specified, start it before the agent
    if setup.orchestrator_address:
        # Start orchestrator
        orchestrator_output = open(outdir / "orchestrator.log", "w")
        if not orchestrator_output:
            print(f"Error opening orchestrator log file in {outdir}")
            exit(1)
        orchestrator = subprocess.Popen(
            [
                orchestrator_exe,
                setup.orchestrator_address,
                *setup.orchestrator_args,
            ],
            stdout=orchestrator_output,
        )
    # Start dool
    try:
        dool = subprocess.Popen(
            ["dool", "-cdlmnyt", "--output", f"{outdir / 'dool.csv'}"],
            stdout=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"Error starting dool: {e}")
        exit(1)
    # Start run
    setup_cmd = setup.cmd(ycsb_exe, status=status)
    print(f"Executing: {setup_cmd}")
    subprocess.run(
        setup_cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
    )
    dool.terminate()
    # Terminate orchestrator and dool
    if setup.orchestrator_address:
        orchestrator.terminate()
    with open(outdir / "setup.json", "w") as f:
        f.write(json.dumps(setup.config, indent=2))
    run_cmd(f"rm -rf {outdir / '.db'}")


class Experiment:
    def __init__(
        self,
        name,
        setups,
        override_timeout,
        override_num_ops,
        override_objsize,
        override_cache_size,
        status=None,
        no_db=False,
        tracesdir=None,
    ):
        self.name = name
        self.setups = {name: setup.__copy__() for name, setup in setups.items()}
        self.override_timeout = override_timeout
        self.override_num_ops = override_num_ops
        self.override_objsize = override_objsize
        self.override_cache_size = override_cache_size
        self.status = status

    def set_timeout(self, timeout):
        for setup in self.setups.values():
            self.override_timeout(setup.config, timeout)

    def set_objsize(self, objsize):
        for setup in self.setups.values():
            self.override_objsize(setup.config, objsize)

    def set_num_ops(self, objsize):
        for setup in self.setups.values():
            self.override_num_ops(setup.config, num_ops)

    def set_cache_size(self, cache_size):
        for setup in self.setups.values():
            self.override_cache_size(setup.config, cache_size)

    def run(self, outdir, bindir, tracesdir=None, only_setup=None, using_slurm=False):
        setups = self.setups.copy()
        if only_setup:
            setups = {only_setup: self.setups[only_setup]}
        for setup_name, setup in setups.items():
            setup_outdir = outdir / self.name / setup.name
            run_cmd(f"rm -rf {setup_outdir}")
            run_cmd(f"mkdir -p {setup_outdir}")
            if using_slurm:
                print(f"[{self.name}] (SLURM) Running '{setup_name}'")
                run_slurm(bindir, setup, setup_outdir, self.status, tracesdir=tracesdir)
            else:
                print(f"[{self.name}] Running '{setup_name}'")
                run(bindir, setup, setup_outdir, self.status, tracesdir=tracesdir)
