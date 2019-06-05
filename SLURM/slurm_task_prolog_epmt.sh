#!/bin/bash
EPMT_PATH=/opt/epmt/epmt
if [ -x $EPMT_PATH ]; then
    if [ ! -z "$SLURM_LOCALID" ] && [ $SLURM_LOCALID == "0" ]; then
	$EPMT_PATH start
    fi
    $EPMT_PATH source 
fi

