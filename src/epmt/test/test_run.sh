#!/bin/bash
set -Eeuo pipefail
# name of script
script=${BASH_SOURCE[0]}

# The below construct checks against unset and null string constructions
# https://stackoverflow.com/questions/3601515/how-to-check-if-a-variable-is-set-in-bash
# It also uses indirect variable reference
check_for_set_var ()
{
    t=$1
    if [ -z ${!t+x} ]; then 
	echo "${script}: ${t} is unset in environment"; 
	exit 1
    fi
}

# If no arguments, we run the test
if [ $# -eq 0 ]; then
    command -V epmt 
    epmt run -- bash $script check
    exit $?
elif [[ $# -ne 1 || $1 != "check" ]]; then
    echo "${script}: invalid arguments, either none or 'check'"
    exit 1
fi

check_for_set_var LD_PRELOAD
check_for_set_var PAPIEX_OUTPUT
check_for_set_var PAPIEX_OPTIONS
