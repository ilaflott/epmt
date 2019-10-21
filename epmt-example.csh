#!/bin/csh

setenv SHELL /bin/csh
setenv SLURM_JOB_ID 1
setenv SLURM_JOB_USER `whoami`
rm -rf ./$SLURM_JOB_ID ./$SLURM_JOB_ID.tgz
rm -rf /tmp/epmt 

./epmt start           # Generate prolog
eval `epmt source`     # Setup environment
# Workload
sleep 1
# End Workload
epmt_uninstrument
epmt stop            # Generate epilog and append
epmt stage           # Move to medium term storage
epmt submit ./$SLURM_JOB_ID.tgz      # Submit from staged storage
rm -f ./$SLURM_JOB_ID.tgz
