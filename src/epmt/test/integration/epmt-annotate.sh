#!/bin/bash -e

# conditional assignment- so this can be tested on a batch node in `salloc` and outside a slurm batch env
export SLURM_JOBID="${SLURM_JOBID:-3456}"
# echo $SLURM_JOBID # DEBUG
epmt start               # Collect job data
epmt annotate inbetween_1=1
epmt -v run sleep 1      # Run command, if no papiex just run command silently
epmt annotate inbetween_2=1
epmt stop                # Generate epilog and append
epmt annotate c=200 d=400
# epmt dump   >/dev/null   # Parse/print job_metadata
f=`epmt stage`           # Move to medium term storage
epmt annotate $f e=300 f=600  # annotate staged job
epmt submit $f           # Submit from staged storage
epmt dump ${SLURM_JOBID} > /dev/null # Force post-process of job
