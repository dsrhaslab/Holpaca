## Dependencies

Holpaca requires the following system and external dependencies:

| Dependency | Version / Ref    | Notes                      |
| ---------- | ---------------- | -------------------------- |
| cachelib   | v20240320_stable | CacheLib library           |
| grpc       | v1.50.1          | gRPC framework             |
| shards     | latest           | MRC generation engine      |
| gsl        | 20211111         | Guidelines Support Library |
| rocksdb    | v6.15.5          | Key-value storage engine   |

> Notes: `rocksdb` is only required for benchmarking purposes. Further, we run a patch for CacheLib in `PoolResizer::work()`.

To build CacheLib and gRPC from source, additional system packages are needed (already included in the container). For **Ubuntu 24.04**, install the following packages:

```bash
binutils-dev, bison, build-essential, cmake, flex, libaio-dev,
libboost-all-dev, libbz2-dev, libdouble-conversion-dev, libdwarf-dev,
libelf-dev, libevent-dev, libfast-float-dev, libgflags-dev, libgoogle-glog-dev,
libiberty-dev, libjemalloc-dev, liblz4-dev, liblzma-dev, libnuma-dev,
libsnappy-dev, libsodium-dev, libssl-dev, libunwind-dev, liburing-dev, make,
pkg-config, zlib1g-dev gcc-11 g++-11
```

To build CacheLib we also need to install the following external projects:

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


Important: you need to set GCC/G++ 11 as the default compilers to build CacheLib.

**If you are following the Docker or Singularity instructions, the installation process already includes GCC/G++ 11.**
