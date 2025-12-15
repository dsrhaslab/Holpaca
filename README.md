# Holpaca Artifact Evaluation

## Overview

**Holpaca** is a cache management framework designed to dynamically optimize cache allocation across multiple pools, while integrating with an orchestrator via gRPC. This artifact provides:

- Control-plane algorithms for cache resizing and performance maximization.  
- Data-plane implementations with CacheLib-based allocators.  
- Benchmarks and evaluation scripts for performance analysis.  

## Hardware and OS Configurations

Experiments were conducted on the following setup:

- **CPU:** 2 × 64-core AMD EPYC 7742  
- **Memory:** 256 GiB RAM  
- **Storage:** 480 GiB SSD  
- **Operating System:** RockyLinux 8  

## Dependencies

Holpaca requires several system and external dependencies:

### System Dependencies

The project can be built on **Ubuntu 24.04** using the following packages:

```bash
binutils-dev, bison, build-essential, cmake, flex, gdb, git, libaio-dev,
libboost-all-dev, libbz2-dev, libdouble-conversion-dev, libdwarf-dev,
libelf-dev, libevent-dev, libfast-float-dev, libgflags-dev, libgoogle-glog-dev,
libiberty-dev, libjemalloc-dev, liblz4-dev, liblzma-dev, libnuma-dev,
libsnappy-dev, libsodium-dev, libssl-dev, libunwind-dev, liburing-dev, make,
pkg-config, pv, python3, python3-pip, wget, zlib1g-dev, zstd
```

Set GCC/G++ 11 as default compilers:

```bash
apt-get install -y gcc-11 g++-11
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 100
update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 100
update-alternatives --set gcc /usr/bin/gcc-11
update-alternatives --set g++ /usr/bin/g++-11
```

### External Project Dependencies

Holpaca relies on the following external projects:

| Dependency | Version / Ref    | Notes                      |
| ---------- | ---------------- | -------------------------- |
| zstd       | v1.5.6           | Compression library        |
| googletest | v1.15.2          | Testing framework          |
| glog       | v0.5.0           | Logging library            |
| gflags     | v2.2.2           | Command-line flags         |
| fmt        | 10.2.1           | Formatting library         |
| sparsemap  | v0.6.2           | Sparse map data structures |
| folly      | commit 17be1d    | Facebook utility library   |
| fizz       | commit 5576ab83  | TLS library                |
| wangle     | commit 0c80d9e   | Networking library         |
| mvfst      | commit aa7ac3    | QUIC implementation        |
| fbthrift   | commit c21dccc   | Thrift RPC library         |
| cachelib   | v20240320_stable | Cache allocator library    |
| grpc       | v1.50.1          | gRPC framework             |
| shards     | latest           | MRC generation engine      |
| gsl        | 20211111         | Guidelines Support Library |
| rocksdb    | v6.15.5          | Key-value storage engine   |

> Note: Some dependencies require additional CMake arguments or pre-build modifications (e.g., CacheLib patch for `PoolResizer::work()`).

---

## Cloning Holpaca

Clone the repository via SSH or HTTPS:

```bash
git clone git@github.com:dsrhaslab/Holpaca.git
# or
git clone https://github.com/dsrhaslab/Holpaca.git

cd Holpaca
```

---

## Building Holpaca

Holpaca can be built using the included `build.py` script.

### `build.py` Arguments

| Argument            | Description                                                         |
| ------------------- | ------------------------------------------------------------------- |
| `-i`                | Install dependencies and targets                                    |
| `-j<n>`             | Number of make jobs for parallel compilation                        |
| `-v`                | Enable verbose output                                               |
| `-p <path>`         | Set installation prefix (default: `./opt/holpaca`)                  |
| `--with-benchmarks` | Build benchmarks                                                    |
| `-d`                | Build in debug mode                                                 |
| `-a`                | Build/install all dependencies                                      |
| `-b <deps>`         | Build/install only a specific list of dependencies (overrides `-a`) |

---

### Recommended Build Methods

For both cases, building the full project (including dependencies) may take up to **1 hour** depending on the hardware.

#### 1. Docker Build

Docker ensures a consistent environment and avoids host dependency issues:

```bash
docker build -t holpaca .
```

By default, the number of make jobs is 4. To customize, use the `MAKE_JOBS` build argument:

```bash
docker build --build-arg MAKE_JOBS=4 -t holpaca .
```

If Docker runs out of space, specify an alternative temporary directory:

```bash
export DOCKER_TMP=/path/to/another/dir
docker build -t holpaca .
```

This builds the full project including benchmarks.

---

#### 2. Singularity Build

Singularity installs the project directly on the host filesystem without containerizing it.

1. Build the Singularity image locally:

```bash
sudo singularity build holpaca.sif singularity.def
```

* Requires `sudo` to install system dependencies.
* Default temporary directory is `/tmp`; override with `--tmpdir` if needed:

```bash
sudo singularity --tmpdir=/path/to/other/tmpdir build holpaca.sif singularity.def
```

2. Transfer to a supercomputer (optional, e.g., Deucalion):

```bash
ssh user@remote-host
cd /parallel/file/system/directories
git clone https://github.com/dsrhaslab/Holpaca
scp path/to/holpaca.sif user@remote-host:/parallel/file/system/directories/Holpaca
cd /parallel/file/system/directories/Holpaca
```

3. Build the project inside the Singularity image:

```bash
singularity run holpaca.sif python3 build.py -i -a -j4 --with-benchmarks
```

> **Note:** The `-j` flag controls the number of parallel make jobs. On a shared login node, reduce this number if necessary to avoid impacting other users.

---

It is important to have a good internet connection for the build to work, as the script will download all dependencies, including external projects.

---

## Running Benchmarks

### Docker

<empty for now>

### Singularity

While still in the Holpaca project:

```bash
cd benchmarks/twitter_traces
```

To run the use-case experiments, you will need to download the Twitter traces:

```bash
singularity run ../holpaca.sif python3 download.py
```

> These traces are capped to a limited number of operations due to their size. Depending on your network connection, the download may take between 30 minutes and 1 hour.

---

## Notes

* Benchmarks require Python dependencies, installed via:

```bash
pip3 install --break-system-packages -r benchmarks/requirements.txt
```

You shouldn't need to install these manually, as they are included in the Docker and Singularity builds.

---

# Disclaimer

The settings used in our experiments were chosen to match the capacities of the compute nodes on Deucalion. You may override these settings, especially if your hardware capabilities are lower. However, results may differ significantly from those reported in the paper, as these setups typically require substantial time to fully warm up and for the optimization and control decisions to impact system performance.
