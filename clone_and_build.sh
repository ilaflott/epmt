#!/bin/bash -e

#epmtREV=7.pip-install
#papiexREV=mkdir-perm-issue
#repo=minimal-metrics-llc/epmt/
#builddir=current_centos_build_epmt

epmtREV=7.pip-install-ubuntu2
papiexREV=ubuntu-build
repo=ilaflott
builddir=current_ubuntu_build_epmt

if [ ! -d $builddir ]
then
    mkdir $builddir
else
    echo "error! builddir exists"
    return
fi

cd $builddir

## Clone up the repos
git clone -b feature/$papiexREV git@gitlab.com:$repo/papiex.git papiex-oss
#sed -i -e '$a[user]' ./papiex/.git/config
#sed -i -e '$a\ \ \ \ email\ =\ ilaflott@gmail.com' ./papiex/.git/config


git clone --recursive -b feature/$epmtREV git@gitlab.com:$repo/epmt.git epmt.git
#sed -i -e '$a[user]' epmt.git/.git/config
#sed -i -e '$a\ \ \ \ email\ =\ ilaflott@gmail.com' epmt.git/.git/config

cd epmt.git

## note- messes with my terminal prompt (PS1)
export PS1="[$(__shortpath "\W") \$] "
exec > >(tee -a "FRESH_clone.log") 2>&1
make release

return
