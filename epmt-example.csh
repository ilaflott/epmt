#!/bin/csh
setenv SHELL /bin/csh
rm -rf ./1 /tmp/epmt/1 ./1.tgz
epmt -j1 start           # Generate prolog
eval `epmt -j1 source`   # Setup environment
epmt -j1 stop            # Generate epilog and append
epmt -j1 stage           # Move to medium term storage
epmt submit ./1.tgz      # Submit from staged storage
rm -f ./1.tgz
