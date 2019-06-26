#!/bin/sh
set -Eeuxo pipefail
USER=testuser
JOB=615503
rm -rf /tmp/epmt
mkdir -p /tmp/epmt/$USER/epmt/$JOB
tar -C /tmp/epmt/$USER/epmt/$JOB -xzf sample/uncollated/postprocruns/ESM4_historical_D151_atmos_18540101.papiex.$JOB.tgz
epmt -v -j $JOB stage
epmt -v submit ./$JOB.tgz
