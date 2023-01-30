#!/bin/bash -e

# Clone up the repos
exec > >(tee -a "FRESH.log") 2>&1

git clone git@gitlab.com:minimal-metrics-llc/epmt/papiex.git
git clone git@gitlab.com:minimal-metrics-llc/epmt/epmt.git
cd epmt.git
# Update the submodules
git submodule update --init --recursive --remote

# Build everything, including papiex, and run the tests
make release-all 
