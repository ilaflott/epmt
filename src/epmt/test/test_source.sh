#!/bin/bash
set -uo pipefail
# name of script
script=${BASH_SOURCE[0]}

check_for_exported_var ()
{
    val=`export -p | grep $1 | sed -e "s/declare -x ${1}=//g" 2>/dev/null`
    if [ $? -eq 1 ]; then
	return 1
    elif [[ $? -eq 0 && -z $val ]]; then
	return 1
    else
	return 0
    fi
}

set -Ee
command -V epmt
set +Ee

eval `epmt source`;

for v in LD_PRELOAD PAPIEX_OUTPUT PAPIEX_OPTIONS; do
    check_for_exported_var $v
    if [ $? -eq 1 ]; then
	echo "${script}: $v not in environment after eval \`epmt source\`"
	exit 1
    fi
done

epmt_uninstrument

for v in LD_PRELOAD PAPIEX_OUTPUT PAPIEX_OPTIONS; do
    check_for_exported_var $v
    if [ $? -eq 0 ]; then
	echo "${script}: $v still in environment after epmt_uninstrument"
	exit 1
    fi
done

epmt_instrument

for v in LD_PRELOAD PAPIEX_OUTPUT PAPIEX_OPTIONS; do
    check_for_exported_var $v
    if [ $? -eq 1 ]; then
	echo "${script}: $v not in environment after epmt_instrument"
	exit 1
    fi
done

exit 0

