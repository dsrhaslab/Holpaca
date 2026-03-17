# ICPE 2026 Artifact Evaluation for Holpaca (#173)
<!-- 
<p align="center"> <img src=".docs/holpaca-logo-transparent.png"/> </p>
<p align="center">
  <sub><em>Artwork generated with the assistance of ChatGPT (OpenAI).</em></sub>
</p> -->

## 📖 Introduction to Holpaca

**Overview:** 
Holpaca is a general-purpose caching middleware that improves the performance and resource efficiency of shared caching environments. Holpaca extends [CacheLib](https://github.com/facebook/CacheLib)’s design by introducing two complementary components: a *data layer*, co-located with each CacheLib instance, which acts as a shim layer between the application and the host caching system to continuously resize the underlying caching blocks; and a *centralized orchestrator* with system-wide visibility, that continuously monitors performance characteristics among the different tenants/instances and dynamically reallocates
memory according to a configurable optimization goal (*e.g.,* maximizing throughput, or ensuring performance isolation).

This artifact is organized with the following contributions:
- Data layer implementation within CacheLib;  
- Centralized orchestrator with two control algorithms for performance maximization and QoS enforcement;  
- Benchmarks and evaluation scripts for performance analysis.  

<p align="center"> <img src=".docs/holpaca-architecture.svg" alt="Holpaca high-level architecture" width="600"/> </p>


## 🖥️ Hardware and OS specifications of the reported experiments

The experiments in the paper were conducted in compute nodes of the [Deucalion](https://docs.macc.fccn.pt/deucalion/) supercomputer, with the following configuration:
- **CPU:** 2× 64-core AMD EPYC 7742  
- **Memory:** 256 GiB RAM  
- **Storage:** 480 GiB SSD  
- **Operating System:** RockyLinux 8, with kernel 4.18.0-348.el8.0.2.x86_64

💡 **Note:** Holpaca is not tied to any specific hardware, and can run on commodity servers as well (for example, 6-core Intel i6 processor, 16 GiB RAM, 256 GiB SSD, with Ubuntu 24.04). Nevertheless, results may differ from those reported in the paper.

---

## Steps to download, install, and test Holpaca

#### Clone the Holpaca repository

```bash
git clone git@github.com:dsrhaslab/Holpaca.git
# or
git clone https://github.com/dsrhaslab/Holpaca.git

cd Holpaca
```

#### 📦 Build the docker image

The artifacts are provided with both Docker and Singularity/Apptainer images. The Singularity/Apptainer is ready for HPC environments. To easy testing, we recommend using the Docker image.

The following commands will install all dependencies and build the Holpaca image. 
If you want, you can check the [full list of dependencies](.docs/dependencies.md).


> ⚠️ This step will take approximately 1 hour (depending on the hardware) and will require approximately 5GB of disk space.

```bash
docker build --build-arg MAKE_JOBS=4 -t holpaca .
```

If Docker runs out of space, specify an alternative temporary directory before the build:

```bash
export DOCKER_TMP=/path/to/another/dir
```

This builds the full project including benchmarks.

#### 🚀 Running the systems

All experiments must be executed **inside the provided Docker container**.  
The general workflow is:

1. Start the container (if not already started)
2. Run experiments 
3. Evaluate results and generate figures  

To run the experiments using Docker, start an interactive container. But, we want to persist downloaded traces and results for them to be available after the container is stopped. 

We recommend running the container with the following command, which mounts the `benchmarks/twitter_traces` and `benchmarks/results` directories as volumes.

```bash
# while in the root of the repository

docker run -it --rm -v ./benchmarks/twitter_traces:/Holpaca/benchmarks/twitter_traces -v ./benchmarks/results:/Holpaca/benchmarks/results  holpaca:latest /bin/bash
```

Next, (while inside the session) navigate to the `benchmarks/twitter_traces` directory and download the Twitter traces:
> ⚠️ This step will require an additional 35GB of disk space.

```bash
cd /Holpaca/benchmarks/twitter_traces
python3 download.py
```

We limit the trace size by the number of operations (otherwise, experiments would take several hours). Nevertheless, the download script will result on 35GB of traces (including a version with unique keys only, `*-keyed`, needed for the loading phase).

After downloading the traces, you can run the experiments.
Experiments are located on the `benchmarks/experiments` directory.

The `benchmarks/experiments/main.py` scripts allows you to choose what experiment to run (optionally with specific parameters).

**Main experiments:** 
> ⚠️ You will require a further 35GB of disk space as the benchmarks will populate the storage backend with the traces (loading phase), which will be deleted after the experiment finishes.

To run the experiments with default parameters (as in the paper), execute:

```bash
cd /Holpaca/benchmarks

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
cd /Holpaca/benchmarks

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
cd /Holpaca/benchmarks

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

**Using Singularity/Apptainer:**

To run Holpaca with Singularity/Apptainer, refer to the file [Run with singularity](.docs/run-singularity.md).

