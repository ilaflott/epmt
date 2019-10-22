setenv SHELL /bin/csh
setenv USER testuser
rm -rf ./1 ./1.tgz
rm -rf /tmp/epmt 
./epmt start -j1           # Generate prolog
eval `epmt source -j1`     # Setup environment
epmt_instrument
echo $PAPIEX_OPTIONS
echo $PAPIEX_OUTPUT
echo $LD_PRELOAD

# Workload
sleep 1
# End Workload
epmt_uninstrument
echo PAPIEX_OPTIONS: $?PAPIEX_OPTIONS
echo PAPIEX_OUTPUT: $?PAPIEX_OUTPUT
echo LD_PRELOAD: $?LD_PRELOAD
./epmt stop -j1            # Generate epilog and append
./epmt stage -j1            # Move to medium term storage
./epmt submit ./1.tgz      # Submit from staged storage
rm -f ./1.tgz
