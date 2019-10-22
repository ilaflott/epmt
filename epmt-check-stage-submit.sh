#!/bin/bash

mkdir -p /tmp/epmt/$SLURM_JOB_USER/$SLURM_JOB_ID
tar -C /tmp/epmt/$SLURM_JOB_USER/$SLURM_JOB_ID -xzf sample/uncollated/postprocruns/short-ESM4_historical_D151_atmos_18540101.papiex.$SLURM_JOB_ID.tgz
epmt -v stage
epmt -v submit ./$SLURM_JOB_ID.tgz
