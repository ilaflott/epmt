#!/bin/csh
set SHELL=/bin/csh
command -V epmt
if ($status != 0) then
    exit 1
endif

eval `./epmt source`;

foreach v (LD_PRELOAD PAPIEX_OUTPUT PAPIEX_OPTIONS)
env | grep $v >& /dev/null
if (($status != 0) || (`eval echo \$$v` == "")) then
    echo "#0: $v not in environment after eval \`epmt source\`"
    exit 1
endif
end

epmt_uninstrument

foreach v (LD_PRELOAD PAPIEX_OUTPUT PAPIEX_OPTIONS)
env | grep $v >& /dev/null
if ($status != 1) then
	echo "$0: $v still in environment after epmt_uninstrument"
	exit 1
endif
end

epmt_instrument

foreach v (LD_PRELOAD PAPIEX_OUTPUT PAPIEX_OPTIONS)
env | grep $v >& /dev/null
if (($status != 0) || (`eval echo \$$v` == "")) then
	echo "$0: $v not in environment after epmt_instrument"
	exit 1
endif
end

exit 0
