#!/bin/bash 

# The task prolog is executed with the same environment as the user tasks to be initiated.
# The standard output of that program is read and processed as follows:
# export name=value sets an environment variable for the user task
# unset name clears an environment variable from the user task
# print ... writes to the task's standard output.
#
# See https://slurm.schedmd.com/prolog_epilog.html
#

# This is edited during install to correct path
EPMT=/opt/epmt/epmt-install/epmt/epmt

err_report() {
    echo "print $0: Error at line $1"
    exit 0
}

trap 'err_report $LINENO' ERR

if [[ -f $EPMT ]] && [[ -x $EPMT ]]; then
    if [[ ! -z "$SLURM_LOCALID" ]] && [[ $SLURM_LOCALID == "0" ]]; then
        $EPMT start
    fi
    $EPMT source --slurm
    # | sed 's/^/export /' | egrep "PAPIEX_OUTPUT=|PAPIEX_OPTIONS=|LD_PRELOAD=" | tr -d ';' 
fi

