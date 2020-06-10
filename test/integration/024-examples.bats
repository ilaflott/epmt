load 'libs/bats-support/load'
load 'libs/bats-assert/load'

teardown() {
    epmt delete 111 222 333 444 2>/dev/null || true
} 

setup() {
    epmt_path=$(dirname `command -v epmt`)
    test -n "${epmt_path}"
    test -d ${epmt_path} || skip "epmt not found in PATH"
    scripts_path=${epmt_path}/../examples
    if [ ! -d ${scripts_path} ]; then
       scripts_path=${epmt_path}
       # in dev env
    fi
    teardown
} 


@test "epmt-example.tcsh" {
      env -i SLURM_JOB_ID=111 PATH=${epmt_path}:${PATH} SLURM_JOB_USER=`whoami` /bin/tcsh -e ${scripts_path}/epmt-example.tcsh 
      assert_success
}
@test "epmt-example.csh" {
      env -i SLURM_JOB_ID=222 PATH=${epmt_path}:${PATH} SLURM_JOB_USER=`whoami` /bin/csh -e ${scripts_path}/epmt-example.csh
      assert_success
}
@test "epmt-example.bash" {
      env -i SLURM_JOB_ID=333 PATH=${epmt_path}:${PATH} SLURM_JOB_USER=`whoami` /bin/bash -Eeu ${scripts_path}/epmt-example.bash
      assert_success
}
@test "epmt-example.sh" {
      env -i SLURM_JOB_ID=444 PATH=${epmt_path}:${PATH} SLURM_JOB_USER=`whoami` /bin/sh -e ${scripts_path}/epmt-example.sh
      assert_success
}
