#!/bin/bash
set -e
service slurmd start
service munge start
service slurmctld start
