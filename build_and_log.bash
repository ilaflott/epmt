#!/bin/bash -e

#exec > >(tee -a "FRESH_build.log") 2>&1
#exec > >(tee -a "FRESH_build_ignore_papiex_tarball_issue.log") 2>&1
exec > >(tee -a "FRESH_epmt_try_chown_make_targ3.log") 2>&1

make release-all
