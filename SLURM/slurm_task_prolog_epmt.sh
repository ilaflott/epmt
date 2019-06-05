#!/bin/bash
if [ ! -z "$SLURM_LOCALID" ] && [ $SLURM_LOCALID == "0" ]; then
    /opt/epmt/epmt start
fi
/opt/epmt/epmt source 

