#!/bin/bash -e

# you will need the following deps installed:
#  sudo apt-get install build-essential libncurses-dev bison flex libssl-dev libelf-dev coreutils

# EPMT_JOB_TAGS='model:linux-kernel;compiler:gcc' ./epmt -a -j kernel-build-$(date +%Y%m%d-%H%M%S) run sample/kernel/build-linux-kernel.sh
#

build_dir=$(tempfile -p epmt -s build)
echo "creating build directory: $build_dir"
rm -rf $build_dir; mkdir -p $build_dir && cd $build_dir

# download
PAPIEX_ARGS="operation:download,operation_count:1;instance:1" wget https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.1.7.tar.xz
PAPIEX_ARGS="operation:extract,operation_count:2;instance:1" tar -xf linux-5.1.7.tar.xz
cd linux-5.1.7

# configure
cp -v /boot/config-$(uname -r) .config
PAPIEX_ARGS="operation:configure,operation_count:3;instance:1" make olddefconfig

# build
PAPIEX_ARGS="operation:build,operation_count:4;instance:1" make -j $(nproc)

