#!/bin/bash
# this script for by-hand usage within container, to be sourced.
# this is targeted at those developing EPMT

echo 2 > /proc/sys/kernel/perf_event_paranoid
install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:|sed 's/papiex-epmt-install/epmt-install/'`
cp -fv ${install_prefix}preset_settings/settings_test_pg_container.py ${install_prefix}epmt/settings.py
ls ${install_prefix}preset_settings/settings_test_pg_container.py
ls ${install_prefix}epmt/settings.py

${install_prefix}epmt/test/integration/libs/bats/install.sh /usr/local
export PATH=$PATH:/usr/local/bin:/usr/local/libexec

echo "" && echo "------ epmt -v check ------" && epmt -v check
echo "" && echo "------ epmt -v unittest ------" && epmt -v unittest
echo "" && echo "------ epmt -v integration ------" && epmt -v integration
