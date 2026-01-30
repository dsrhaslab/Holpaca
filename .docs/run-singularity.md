#### 📦 Build the Singularity/Apptainer image (and install Holpaca)
> ⚠️ This step will take approximately 1 hour, depending on the hardware

Instead of using Docker, you can use Singularity/Apptainer to build and run Holpaca, which is more suitable for HPC environments. 
Be aware that Singularity/Apptainer do not containerize a separate filesystem like Docker, but rather share the host filesystem. As such, this process will install the project directly on the host filesystem. 

First, we need to install the dependencies. 

```bash
# Requires `sudo` to install system dependencies.
sudo singularity build holpaca.sif singularity.def
```

If Singularity runs out of space, specify an alternative temporary directory before the build:

```bash
sudo singularity --tmpdir=/path/to/other/tmpdir build holpaca.sif singularity.def
```

Second, we need to build the project using the Singularity image:

```bash
singularity run holpaca.sif python3 build.py -i -a -j4 --with-benchmarks -v
```

> **Note:** The `-j` flag controls the number of parallel make jobs. 


#### 🚀 Running the systems

All experiments must be executed **using the constructed Singularity/Apptainer image**.

To run the experiments using Singularity/Apptainer, start an interactive session:

```bash
# While in the Holpaca root directory
singularity shell holpaca.sif
```

Next, navigate to the `benchmarks/twitter_traces` directory and download the Twitter traces:

```bash
# While in the Holpaca root directory and inside the Singularity/Apptainer shell
cd benchmarks/twitter_traces
python3 download.py
```

We limit the trace size by the number of operations (otherwise, experiments would take several hours). Nevertheless, the download script will result on 35GB of traces (including a version with unique keys only, `*-keyed`, needed for the loading phase).

After downloading the traces, you can run the experiments.
Experiments are located on the `benchmarks/experiments` directory.

The `benchmarks/experiments/main.py` scripts allows you to choose what experiment to run (optionally with specific parameters).

**Main experiments:**

To run the experiments with default parameters (as in the paper), execute:

```bash
# While in the Holpaca root directory and inside the Singularity/Apptainer shell
cd benchmarks

# 5.1 Single instance with multiple tenants (Figure 5)
python3 experiments/main.py use_case_1 -t twitter_traces 

# 5.2 Multiple instances (Figure 6)
python3 experiments/main.py use_case_2 -t twitter_traces

# 5.3 Per-instance QoS guarantees (Figure 7)
python3 experiments/main.py use_case_3 -t twitter_traces
```
> Note: these scripts will generate the output logs. Check the visualization commands below for generating the plots.
> ⚠️ Each test will take approximately 1.5 hours per setup ((loading time (0.5) + execution time (1)) * setups (3) = approximately 4.5 hours)

These scripts execute all setups (`baseline`, `optimizer`, and `holpaca`) sequentially, each with a duration of loading phase (populating the storage backend) and approximately an hour of a running phase. 
To test each individual setup, use the `-s` flag with the corresponding system name, namely `baseline`, `optimizer`, `holpaca`.

Additionally, to run shorter experiments, you can use the `-m` to set the maximum execution time (in seconds) of the running phase (*i.e.,* not applicable to the loading phase). For example, to run for only 5 minutes add the flag `-m 300`. 
> Note: using a shorter execution time might lead to different results from those observed in the paper, due to cache warmup and incomplete trace replaying.

**Holpaca's overhead:**

To reproduce the overhead experiments, use the following scripts:

```bash
# Figure 8
python3 experiments/main.py agent_overhead 

# Table 1
python3 experiments/main.py orchestrator_algorithm_latency_breakdown

# Table 2
python3 experiments/main.py orchestrator_control_interval
```

The overhead experiments (`agent_overhead`, `orchestrator_algorithm_latency_breakdown`, and `orchestrator_control_interval`) have durations of 10 minutes, but include at least 60 setups each. 

📈 **Output and visualization:**

The results of the experiments will be, by default, stored in the `benchmarks/results` directory. 
To visualize the results, you can use the provided plotting scripts in the `benchmarks/plots` directory.

All scripts take as input the path to the results directory. Please be sure to use the script that matches the experiment you ran. 

```bash
# Figure 5
python3 plots/use_case_1.py results/use_case_1

# Figure 6
python3 plots/use_case_2.py results/use_case_2

# Figure 7
python3 plots/use_case_3.py results/use_case_3

# Figure 8
python3 plots/agent_overhead.py results/agent_overhead
```
> **Note:** these plotting scripts assume the results/logs from **all setups** are available. Trying to plot incomplete results may lead to errors. 

**Motivation:**

We also provide scripts to run and plot the motivation experiments (`motivation_1` and `motivation_2`).

*** 

**Using Singularity/Apptainer on Slurm-based HPC clusters:**

To run experiments on Slurm-based HPC clusters using Singularity/Apptainer, take a look at the provided script `benchmarks/with_slurm/submit_job.py`. This script can be used to submit jobs to the Slurm scheduler, i.e. one job per experiment setup. If you only want to run a specific setup or experiment (or pass experiment flags), you can modify the script accordingly.
