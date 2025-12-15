#!/usr/bin/env python3
import argparse
import os
import subprocess
from pathlib import Path

CWD = Path(__file__).parent.resolve().absolute()
EXTERNAL = CWD / "external"


class Dependency:
    def __init__(
        self,
        name,
        url,
        ref="main",
        commit=None,
        git_opts=[],
        source_dir=".",
        cmake_args={},
        pre_build_cmds=[],
    ):
        self.name = name
        self.url = url
        self.ref = ref
        self.commit = commit
        self.git_opts = git_opts
        self.source_dir = source_dir
        self.cmake_args = cmake_args
        self.pre_build_cmds = pre_build_cmds


class Target:
    def __init__(self, name, source_dir, cmake_args={}):
        self.name = name
        self.source_dir = source_dir
        self.cmake_args = cmake_args


def run(cmd, cwd=None):
    """Run command and exit on failure."""
    print(f"Running: {cmd}")
    subprocess.run(cmd, cwd=cwd, check=True, shell=True)


deps = {
    "zstd": Dependency(
        name="zstd",
        url="https://github.com/facebook/zstd",
        ref="v1.5.6",
        source_dir="build/cmake",
        cmake_args={"ZSTD_BUILD_TESTS": "OFF"},
    ),
    "googletest": Dependency(
        name="googletest",
        url="https://github.com/google/googletest",
        ref="v1.15.2",
    ),
    "glog": Dependency(
        name="glog",
        url="https://github.com/google/glog",
        ref="v0.5.0",
        cmake_args={"WITH_GFLAGS": "OFF"},
    ),
    "gflags": Dependency(
        name="gflags",
        url="https://github.com/gflags/gflags",
        ref="v2.2.2",
        cmake_args={"GFLAGS_BUILD_TESTING": "NO"},
    ),
    "fmt": Dependency(
        name="fmt",
        url="https://github.com/fmtlib/fmt",
        ref="10.2.1",
        cmake_args={"FMT_TEST": "NO"},
    ),
    "sparsemap": Dependency(
        name="sparsemap",
        url="https://github.com/Tessil/sparse-map",
        ref="v0.6.2",
        git_opts=["--recurse-submodules", "--shallow-submodules"],
    ),
    "folly": Dependency(
        name="folly",
        url="https://github.com/facebook/folly",
        commit="17be1d",
        git_opts=["--recurse-submodules", "--shallow-submodules"],
        cmake_args={"BUILD_TESTS": "OFF"},
    ),
    "fizz": Dependency(
        name="fizz",
        url="https://github.com/facebookincubator/fizz",
        commit="5576ab83",
        git_opts=["--recurse-submodules", "--shallow-submodules"],
        source_dir="fizz",
        cmake_args={"BUILD_TESTS": "OFF"},
    ),
    "wangle": Dependency(
        name="wangle",
        url="https://github.com/facebook/wangle",
        commit="0c80d9e",
        git_opts=["--recurse-submodules", "--shallow-submodules"],
        source_dir="wangle",
        cmake_args={"BUILD_TESTS": "OFF"},
    ),
    "mvfst": Dependency(
        name="mvfst",
        url="https://github.com/facebook/mvfst",
        commit="aa7ac3",
        git_opts=["--recurse-submodules", "--shallow-submodules"],
    ),
    "fbthrift": Dependency(
        name="fbthrift",
        url="https://github.com/facebook/fbthrift",
        commit="c21dccc",
        git_opts=["--recurse-submodules", "--shallow-submodules"],
        cmake_args={"CMAKE_BUILD_WITH_INSTALL_RPATH": "FALSE"},
    ),
    "cachelib": Dependency(
        name="cachelib",
        url="https://github.com/facebook/CacheLib",
        ref="v20240320_stable",
        source_dir="cachelib",
        cmake_args={"BUILD_TESTS": "OFF", "CMAKE_FIND_DEBUG_MODE": "ON"},
        pre_build_cmds=[
            rf"""sed -i '2319,2322c\    return filterCompactCachePools(allocator_->getPoolsOverLimit());' {EXTERNAL}/cachelib/cachelib/allocator/CacheAllocator-inl.h"""
        ],  # Fix for PoolResizer::work()
    ),
    "grpc": Dependency(
        name="grpc",
        url="https://github.com/grpc/grpc",
        ref="v1.50.1",
        git_opts=["--recurse-submodules", "--shallow-submodules"],
        cmake_args={
            "gRPC_INSTALL": "ON",
            "gRPC_BUILD_TESTS": "OFF",
            "gRPC_ZLIB_PROVIDER": "package",
            "gRPC_SSL_PROVIDER": "package",
            "ABSL_PROPAGATE_CXX_STD": "ON",
            "protobuf_WITH_ZLIB": "ON",
            "CMAKE_BUILD_WITH_INSTALL_RPATH": "FALSE",
        },
    ),
    "shards": Dependency(
        name="shards",
        url="https://github.com/dsrhaslab/SHARDS-cpp",
    ),
    "gsl": Dependency(
        name="gsl",
        url="https://github.com/ampl/gsl",
        ref="20211111",
        cmake_args={
            "GSL_DISABLE_TESTS": 1,
            "DOCUMENTATION": "OFF",
            "NO_AMPL_BINDINGS": 1,
        },
    ),
    "rocksdb": Dependency(
        name="rocksdb",
        url="https://github.com/facebook/rocksdb",
        ref="v6.15.5",
        cmake_args={"WITH_TESTS": "OFF", "WITH_GFLAGS": "OFF"},
    ),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--build-all-deps", action="store_true", help="Build all dependencies"
    )
    parser.add_argument(
        "-i", "--install", action="store_true", help="Build and install Holpaca"
    )
    parser.add_argument(
        "-b",
        "--build-deps",
        nargs="*",
        help="Build only specified dependencies (overrides --build-all-deps)",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        default=str(CWD / "opt" / "holpaca"),
        type=str,
        help="Installation prefix",
    )
    parser.add_argument(
        "-j", "--jobs", type=int, default=1, help="Number of parallel build jobs"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Build in debug mode"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose build output"
    )
    parser.add_argument(
        "--with-benchmarks", action="store_true", help="Build benchmarks"
    )
    args = parser.parse_args()

    install_deps = []

    if args.build_deps is not None:
        for depname in args.build_deps:
            if depname not in deps:
                raise ValueError(f"Unknown dependency: {depname}")
        install_deps = args.build_deps
    elif args.build_all_deps:
        install_deps = list(deps.keys())

    prefix = Path(args.prefix).resolve()
    build_type = "Debug" if args.debug else "Release"

    # Setup environment
    env_paths = {
        "CMAKE_PREFIX_PATH": f"{prefix}/lib/cmake:{prefix}/lib64/cmake:{prefix}",
        "PKG_CONFIG_PATH": f"{prefix}/lib/pkgconfig:{prefix}/lib64/pkgconfig",
        "LD_LIBRARY_PATH": f"{prefix}/lib:{prefix}/lib64",
        "LIBRARY_PATH": f"{prefix}/lib:{prefix}/lib64",
        "PATH": f"{prefix}/bin:{os.environ.get('PATH', '')}",
    }
    for k, v in env_paths.items():
        os.environ[k] = f"{v}:{os.environ.get(k, '')}"

    cmake_flags = {
        "CMAKE_INSTALL_PREFIX": f"{prefix}",
        "CMAKE_MODULE_PATH": f"{prefix}/lib/cmake;{EXTERNAL}/{deps['cachelib'].name}/{deps['cachelib'].source_dir}/cmake",
        "BUILD_SHARED_LIBS": "ON",
        "CMAKE_BUILD_TYPE": f"{build_type}",
        "CMAKE_VERBOSE_MAKEFILE": "ON" if args.verbose else "OFF",
        "CMAKE_INSTALL_RPATH": f"{prefix}/lib:{prefix}/lib64",
        "CMAKE_INSTALL_RPATH_USE_LINK_PATH": "FALSE",
        "CMAKE_BUILD_WITH_INSTALL_RPATH": "TRUE",
    }

    targets = [Target(name="holpaca", source_dir="holpaca")]

    if args.with_benchmarks:
        targets.append(Target(name="YCSB-cpp", source_dir="benchmarks/YCSB-cpp"))

    if install_deps != []:
        EXTERNAL.mkdir(parents=True, exist_ok=True)

        # Clone and build each dependency
        for depname in install_deps:
            dep = deps[depname]

            target = EXTERNAL / dep.name
            if target.exists():
                run(f"rm -rf {target}")

            # Clone
            run(
                f"git clone -b {dep.ref} --depth 1 {' '.join(dep.git_opts)} {dep.url} {target}"
            )

            # Checkout specific commit if provided
            if dep.commit:
                run(f"git fetch --unshallow", cwd=target)
                run(f"git checkout {dep.commit}", cwd=target)

            # Pre-build commands
            for cmd in dep.pre_build_cmds:
                run(cmd)

            # Build
            build_dir = f"build-{dep.name}"
            source_path = target / dep.source_dir
            # remove build dir if it exists
            run(f"rm -rf {build_dir}")
            parsed_cmake_flags = " ".join(
                [f'-D{k}="{v}"' for k, v in {**cmake_flags, **dep.cmake_args}.items()]
            )
            run(f"cmake {parsed_cmake_flags} -B{build_dir} -S{source_path}")

            if args.install:
                run(f"make -C{build_dir} -j{args.jobs} install")
            else:
                run(f"make -C{build_dir} -j{args.jobs}")

    # Build targets
    for target in targets:
        build_dir = f"build-{target.name}"
        parsed_cmake_flags = " ".join(
            [f'-D{k}="{v}"' for k, v in {**cmake_flags, **target.cmake_args}.items()]
        )
        run(f"cmake {parsed_cmake_flags} -B{build_dir} -S{target.source_dir}")
        if args.install:
            run(f"make -C{build_dir} -j{args.jobs} install")
        else:
            run(f"make -C{build_dir} -j{args.jobs}")


if __name__ == "__main__":
    main()
