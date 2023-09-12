#!/bin/bash -e

#epmtREV=7.pip-install
#papiexREV=mkdir-perm-issue
#repo=minimal-metrics-llc/epmt
#builddir=current_centos_build_epmt

#epmtREV=feature/7.pip-install-ubuntu
#epmtREV=feature/7.pip-install-ubuntu2
epmtREV=feature/7.pip-install-ubuntu2.diff.build.reqs
papiexREV=feature/ubuntu-build
repo=ilaflott
builddir=diff_ubuntu_build_epmt
    


function clone_epmt(){
    
    [ ! -d $builddir ] || echo "error! builddir exists"
    [ -d $builddir ] && return 
    mkdir $builddir && cd $builddir
    
     ## Clone up the repos
    git clone -b $papiexREV --single-branch git@gitlab.com:$repo/papiex.git papiex-oss
    gsed -i -e '$a[user]' ./papiex-oss/.git/config
    gsed -i -e '$a\ \ \ \ email\ =\ ilaflott@gmail.com' ./papiex-oss/.git/config
    
    git clone -b $epmtREV --single-branch git@gitlab.com:$repo/epmt.git epmt.git
    gsed -i -e '$a[user]' epmt.git/.git/config
    gsed -i -e '$a\ \ \ \ email\ =\ ilaflott@gmail.com' epmt.git/.git/config

    cd epmt.git && git submodule update --init --recursive --remote
    cp ../../clone_and_build.sh .
    
    return
}


function build_epmt(){
    ## note- messes with my terminal prompt (PS1)
    export OLD_PS1=$PS1
    export PS1="[$(__shortpath "\W") \$] "
    if [ -f FRESH.log ]; then rm -f FRESH.log; fi 
    exec > >(tee -a "FRESH.log") 2>&1
    make release
    return
}    


