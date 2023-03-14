#!/bin/sh

epmt start           # Generate prolog
eval `epmt source`   # Setup environment
/bin/sleep 1 2>/dev/null >&2 # Workload
epmt_uninstrument    # End Workload, disable instrumentation
epmt stop            # Wrap up job stats
f=`epmt stage`       # Move to medium term storage ($PWD)
epmt submit $f       # Submit to DB
epmt dump 2> /dev/null >&2 # Post process
epmt delete $SLURM_JOB_ID  # Delete
