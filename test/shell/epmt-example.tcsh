#!/bin/tcsh

setenv SHELL /bin/tcsh
epmt start             # Generate prolog
eval `epmt source`     # Setup environment
/bin/sleep 1 >& /dev/null   # Workload
epmt_uninstrument      # End Workload
epmt stop              # Wrap up job stats
set f=`epmt stage`     # Move to medium term storage ($PWD)
epmt submit $f         # Submit to DB
epmt dump >& /dev/null # Post process
epmt delete $SLURM_JOB_ID # Remove