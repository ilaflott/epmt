#!/bin/bash
unset LD_PRELOAD
EPMT_PATH=/opt/epmt/epmt-install/epmt
if [ -x $EPMT_PATH ]; then
    if [ ! -z "$SLURM_LOCALID" ] && [ $SLURM_LOCALID == "0" ]; then
	$EPMT_PATH stop
    fi
fi
