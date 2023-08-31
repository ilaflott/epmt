#!/bin/bash -e

function build_epmt(){
    ## note- messes with my terminal prompt (PS1)
    export OLD_PS1=$PS1
    export PS1="[$(__shortpath "\W") \$] "
    if [ -f FRESH.log ]; then rm -f FRESH.log; fi 
    exec > >(tee -a "FRESH.log") 2>&1
    make release
    #make check-release
    #export PS1=$OLD_PS1
}    


function clone_epmt(){
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
    
     ## Clone up the repos
    git clone -b feature/$papiexREV git@gitlab.com:$repo/papiex.git papiex-oss
    gsed -i -e '$a[user]' ./papiex-oss/.git/config
    gsed -i -e '$a\ \ \ \ email\ =\ ilaflott@gmail.com' ./papiex-oss/.git/config
    
    
    #git clone --recursive -b feature/$epmtREV git@gitlab.com:$repo/epmt.git epmt.git
    git clone -b feature/$epmtREV git@gitlab.com:$repo/epmt.git epmt.git
    gsed -i -e '$a[user]' epmt.git/.git/config
    gsed -i -e '$a\ \ \ \ email\ =\ ilaflott@gmail.com' epmt.git/.git/config
    cp ./clone_and_build.sh ./epmt.git && cd epmt.git
    
    git submodule update --init --recursive --remote
    
     return
 }
