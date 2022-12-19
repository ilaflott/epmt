#!/bin/bash -e
TAG=4.9.2-rc1

# Clone up the repos
exec > >(tee -a "FRESH.log") 2>&1

git clone -b papiex-epmt --single-branch git@gitlab.com:minimal-metrics-llc/papiex.git papiex-oss
git clone -b $TAG --single-branch git@gitlab.com:minimal-metrics-llc/epmt/epmt.git epmt.git
cd epmt.git
# Update the submodules
git submodule update --init --recursive --remote

# Build everything, including papiex, and run the tests
make release-all 
