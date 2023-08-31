#!/bin/bash -e

#epmtREV=7.pip-install
#papiexREV=mkdir-perm-issue
#repo=minimal-metrics-llc/epmt/
#builddir=current_centos_build_epmt

epmtREV=7.pip-install-ubuntu2
papiexREV=ubuntu-build
repo=ilaflott
builddir=current_ubuntu_build_epmt


[ ! -d $builddir ] || echo "error! builddir exists"
[ -d $builddir ] && return 
mkdir $builddir && cd $builddir

#if [ ! -d $builddir ]
#then
#    mkdir $builddir
#else
#    echo "error! builddir exists"
#    return
#fi



## Clone up the repos
git clone -b feature/$papiexREV git@gitlab.com:$repo/papiex.git papiex-oss
gsed -i -e '$a[user]' ./papiex-oss/.git/config
gsed -i -e '$a\ \ \ \ email\ =\ ilaflott@gmail.com' ./papiex-oss/.git/config


#git clone --recursive -b feature/$epmtREV git@gitlab.com:$repo/epmt.git epmt.git
git clone -b feature/$epmtREV git@gitlab.com:$repo/epmt.git epmt.git
gsed -i -e '$a[user]' epmt.git/.git/config
gsed -i -e '$a\ \ \ \ email\ =\ ilaflott@gmail.com' epmt.git/.git/config

cp ./clone_and_build.sh ./epmt.git
cd epmt.git
git submodule update --init --recursive --remote

#comment this return out to clone + build without stopping. 
return

## note- messes with my terminal prompt (PS1)
export PS1="[$(__shortpath "\W") \$] "
exec > >(tee -a "FRESH_clone.log") 2>&1
make release

return
