setenv SHELL /bin/csh
setenv USER testuser
rm -rf ./1 ./1.tgz
rm -rf /tmp/epmt 
epmt -j1 start           # Generate prolog
eval `epmt -j1 source`   # Setup environment
# Workload
sleep 1
# End Workload
unsetenv LD_PRELOAD
epmt -j1 stop            # Generate epilog and append
epmt -j1 stage           # Move to medium term storage
epmt submit ./1.tgz      # Submit from staged storage
rm -f ./1.tgz