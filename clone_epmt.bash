#!/bin/bash -e

# this script just clones the repo and makes a log!
TAG=4.9.2-rc2

# Clone up the repos                                                  
exec > >(tee -a "FRESH_clone.log") 2>&1

START_DIR=$PWD
cd current_build

git clone -b papiex-epmt --single-branch git@gitlab.com:minimal-metrics-llc/papiex.git papiex-oss
git clone -b $TAG --single-branch git@gitlab.com:minimal-metrics-llc/epmt/epmt.git epmt.git
cd epmt.git
# Update the submodules                                                
git submodule update --init --recursive --remote

cp $START_DIR/Makefile .
cp $START_DIR/FRESH_clone.log .

return

# Build everything, including papiex, and run the tests                                
#make release-all
