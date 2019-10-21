#!/bin/csh

setenv SHELL /bin/tcsh
./epmt start           # Generate prolog
eval `epmt source`     # Setup environment
sleep 1                # Workload
epmt_uninstrument      # End Workload
epmt stop              # Wrap up job stats
epmt stage             # Move to medium term storage ($PWD)
epmt submit ./$SLURM_JOB_ID.tgz # Submit to DB

