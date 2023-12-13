#!/bin/bash -e

function build_epmt(){
    ## note- messes with my terminal prompt (PS1)
#    export OLD_PS1=$PS1
#    export PS1="[$(__shortpath "\W") \$] "
    if [ -f FRESH.log ]; then rm -f FRESH.log; fi 
    exec > >(tee -a "FRESH.log") 2>&1
    make release
    #make check-release
    #export PS1=$OLD_PS1
}    




function clone_epmt(){
    #repo=minimal-metrics-llc/epmt
    #epmtREV=feature/7.pip-install
    #papiexREV=papiex-epmt
    builddir=current_centos_build_epmt
    #builddir=DONOTEDIT_current_centos_build_epmt

    repo=ilaflott
    epmtREV=feature/7.pip-install
    #epmtREV=feature/7.pip-install-ubuntu2
    #papiexREV=papiex-epmt
    #builddir=current_ubuntu_build_epmt
    
    
    if [ ! -d $builddir ]; then
	mkdir $builddir
    else
	echo "error! builddir exists. stop."
	return
    fi
    
    ## Clone up the repos          git@gitlab.com:minimal-metrics-llc/epmt/epmt.git
    #echo "cloning -b $papiexREV git@gitlab.com:$repo/papiex.git"
    #git clone -b $papiexREV git@gitlab.com:$repo/papiex.git papiex-oss && cd papiex-oss
    #gitlocalconf gitlab
    #cd -
    
    if [ ! -d ./COPY_ME ]; then
	mkdir COPY_ME && cd COPY_ME
	echo "cloning -b feature/$epmtREV git@gitlab.com:$repo/epmt.git epmt.git"
	git clone -b $epmtREV git@gitlab.com:$repo/epmt.git epmt.git && cd epmt.git
	git submodule update --init --recursive --remote
	gitlocalconf gitlab.com
	cd ../..
    fi

    cp -r ./COPY_ME/epmt.git $builddir/. && cd $builddir/epmt.git    
    #rm -f Makefile && cp ../../my_centos_build_Makefile Makefile
    #mv Makefile ORIG_BACKUP_M8KEFILE && cp ../../my_centos_build_Makefile Makefile
    #export PATH=$PATH:$PWD
     
    return
}




function old_clone_epmt(){
    repo=minimal-metrics-llc/epmt
    epmtREV=feature/7.pip-install
    papiexREV=papiex-epmt
    builddir=current_centos_build_epmt
    #builddir=DONOTEDIT_current_centos_build_epmt

    #repo=ilaflott    
    #epmtREV=feature/7.pip-install-ubuntu2
    #papiexREV=papiex-epmt
    #builddir=current_ubuntu_build_epmt
    
    
    if [ ! -d $builddir ]; then
	mkdir $builddir && cd $builddir
    else
	echo "error! builddir exists. stop."
	return
    fi
    
    ## Clone up the repos          git@gitlab.com:minimal-metrics-llc/epmt/epmt.git
    echo "cloning -b $papiexREV git@gitlab.com:$repo/papiex.git"
    git clone -b $papiexREV git@gitlab.com:$repo/papiex.git papiex-oss && cd papiex-oss
    gitlocalconf gitlab
    cd -
    

    echo "cloning -b feature/$epmtREV git@gitlab.com:$repo/epmt.git epmt.git"
    git clone -b $epmtREV git@gitlab.com:$repo/epmt.git epmt.git && cd epmt.git
    gitlocalconf gitlab
    git submodule update --init --recursive --remote
    
    return
}
