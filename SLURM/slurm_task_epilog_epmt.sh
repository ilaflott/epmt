#!/bin/bash
EPMT_PATH=/opt/epmt/epmt
if [ -x $EPMT_PATH ]; then
    unset LD_PRELOAD
    $EPMT_PATH stop
fi
