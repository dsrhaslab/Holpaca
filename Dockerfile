FROM ubuntu:24.04

# Show the build process
ENV PYTHONUNBUFFERED=1

# Define the number of parallel jobs for building
ARG MAKE_JOBS=4

# Install system dependencies
RUN set -eux; \
    echo 'tzdata tzdata/Areas select Etc' | debconf-set-selections; \
    echo 'tzdata tzdata/Zones/Etc select UTC' | debconf-set-selections; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        binutils-dev \
        bison \
        build-essential \
        cmake \
        flex \
        gdb \
        git \
        libaio-dev \
        libboost-all-dev \
        libbz2-dev \
        libdouble-conversion-dev \
        libdwarf-dev \
        libelf-dev \
        libevent-dev \
        libfast-float-dev \
        libgflags-dev \
        libgoogle-glog-dev \
        libiberty-dev \
        libjemalloc-dev \
        liblz4-dev \
        liblzma-dev \
        libnuma-dev \
        libsnappy-dev \
        libsodium-dev \
        libssl-dev \
        libunwind-dev \
        liburing-dev \
        make \
        pkg-config \
        pv \
        python3 \
        python3-pip \
        wget \
        zlib1g-dev \
        zstd

# Set gcc-11 and g++-11 as default compilers
RUN apt-get install -y --no-install-recommends gcc-11 g++-11; \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 100; \
    update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 100; \
    update-alternatives --set gcc /usr/bin/gcc-11; \
    update-alternatives --set g++ /usr/bin/g++-11; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# Copy everything except what is excluded via .dockerignore
COPY . /Holpaca

# Install python packages 
RUN pip3 install --break-system-packages -r /Holpaca/benchmarks/requirements.txt

# Set this project as the working directory
WORKDIR /Holpaca

# Git config to avoid potential issues during cloning large repositories
RUN git config --global http.version HTTP/1.1 \
 && git config --global http.retry 10 \
 && git config --global http.postBuffer 524288000

# Install project
RUN ./build.py -a -j${MAKE_JOBS} -i --with-benchmarks -v -p opt/holpaca
