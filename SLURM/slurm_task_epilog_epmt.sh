#!/bin/bash
unset LD_PRELOAD
EPMT=/opt/epmt/epmt-install/epmt/epmt

err_report() {
    echo "$0: Error at line $1" 
    exit 0
}

trap 'err_report $LINENO' ERR

if [[ -f $EPMT ]] && [[ -x $EPMT ]]; then
    if [[ ! -z "$SLURM_LOCALID" ]] && [[ $SLURM_LOCALID == "0" ]]; then
	$EPMT stop 
	$EPMT stage
    fi
fi
