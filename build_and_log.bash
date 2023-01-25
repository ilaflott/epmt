#!/bin/bash -e

exec > >(tee -a "FRESH_build.log") 2>&1

make release-all
