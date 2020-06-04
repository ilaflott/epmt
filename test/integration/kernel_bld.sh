#!/bin/bash -e

# you will need the following deps installed:
#  sudo apt-get install build-essential libncurses-dev bison flex libssl-dev libelf-dev coreutils

# EPMT_JOB_TAGS='model:linux-kernel;compiler:gcc' ./epmt -a -j kernel-build-$(date +%Y%m%d-%H%M%S) run sample/kernel/build-linux-kernel.sh
#

build_dir=$(tempfile -p epmt -s build)
echo "creating build directory: $build_dir"

function finish {
  # Your cleanup code here
  rm -rf $build_dir
}
trap finish EXIT

rm -rf $build_dir; mkdir -p $build_dir && cd $build_dir

# download
PAPIEX_TAGS="op:download;op_instance:1;op_sequence:1" wget https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.1.7.tar.xz
PAPIEX_TAGS="op:untar;op_instance:1;op_sequence:1" tar -xf linux-5.1.7.tar.xz
cd linux-5.1.7

# configure
# cp -v /boot/config-$(uname -r) .config
PAPIEX_TAGS="op:configure;op_instance:1;op_sequence:1" make tinyconfig

# build
PAPIEX_TAGS="op:compile;op_instance:1;op_sequence:1" make -j $(nproc)
