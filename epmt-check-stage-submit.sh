#!/bin/bash
set -Eeuxo pipefail
export USER=testuser
JOB=615503
rm -rf /tmp/epmt
mkdir -p /tmp/epmt/$USER/epmt/$JOB
tar -C /tmp/epmt/$USER/epmt/$JOB -xzf sample/uncollated/postprocruns/short-ESM4_historical_D151_atmos_18540101.papiex.$JOB.tgz
epmt -v stage -j $JOB
epmt -v submit ./$JOB.tgz
