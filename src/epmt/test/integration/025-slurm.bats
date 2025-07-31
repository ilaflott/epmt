load 'libs/bats-support/load'
load 'libs/bats-assert/load'

verify_staged_file() {
  local wait_seconds=10
  oldpwd=`pwd`
  cd ${stage_dest}
  until test $wait_seconds -eq 0 || ls -t *.tgz >/dev/null 2>&1 ; do sleep 1; (( wait_seconds-- )); done
  tgz=$(ls -t *.tgz | head -n 1)
  test -s $tgz
  tar xf $tgz
  test -s job_metadata
  test -s *-collated-papiex-*-*.csv || ( test -s *-papiex.tsv && test -s *-papiex-header.tsv )
  rm -f $tgz job_metadata *-collated-papiex-*-*.csv *-papiex*.tsv
  cd $oldpwd;
  echo "$cmd PASSED"
}

setup() {
  command -v sinfo > /dev/null || skip
  command -v srun > /dev/null || skip
  command -v sbatch > /dev/null || skip
  stage_dest=$(epmt -h | sed -n 's/stage_command_dest://p')
  # echo "stage_dest:${stage_dest}"
  test -n "${stage_dest}" || fail
  test -d ${stage_dest} || fail
  resource_path=$(python -c "import epmt, os; print(os.path.dirname(os.path.dirname(epmt.__file__)))")
  # echo "resource_path:${resource_path}"
  test -n "${resource_path}" || fail
  test -d ${resource_path} || fail
  bash -c 'echo -e "#!/bin/tcsh\nsleep 1\n" > /tmp/sleeptest.tcsh'
  bash -c 'echo -e "#!/bin/csh\nsleep 1\n" > /tmp/sleeptest.csh'
  bash -c 'echo -e "#!/bin/bash\nsleep 1\n" > /tmp/sleeptest.bash'
  bash -c 'echo -e "#!/bin/sh\nsleep 1\n" > /tmp/sleeptest.sh'
  chmod +x /tmp/sleeptest.*sh
} 

teardown() {
  rm -f sleeptest.tcsh sleeptest.csh sleeptest.bash sleeptest.sh
} 

@test "sbatch epmt-example.tcsh" {
      sbatch ${resource_path}/examples/epmt-example.tcsh 
      assert_success
      verify_staged_file
      assert_success
}
@test "sbatch epmt-example.csh" {
      sbatch ${resource_path}/examples/epmt-example.csh
      assert_success
      verify_staged_file
      assert_success      
}
@test "sbatch epmt-example.bash" {
      sbatch ${resource_path}/examples/epmt-example.bash
      assert_success
      verify_staged_file
      assert_success
}
@test "sbatch epmt-example.sh" {
      sbatch ${resource_path}/examples/epmt-example.sh
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (inline)" {
      srun -n1 --task-prolog="${resource_path}/slurm/slurm_task_prolog_epmt.sh" --task-epilog="${resource_path}/slurm/slurm_task_epilog_epmt.sh" sleep 1
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (tcsh)" {
      srun -n1 --task-prolog="${resource_path}/slurm/slurm_task_prolog_epmt.sh" --task-epilog="${resource_path}/slurm/slurm_task_epilog_epmt.sh" /tmp/sleeptest.tcsh
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (csh)" {
      srun -n1 --task-prolog="${resource_path}/slurm/slurm_task_prolog_epmt.sh" --task-epilog="${resource_path}/slurm/slurm_task_epilog_epmt.sh" /tmp/sleeptest.csh
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (bash)" {
      srun -n1 --task-prolog="${resource_path}/slurm/slurm_task_prolog_epmt.sh" --task-epilog="${resource_path}/slurm/slurm_task_epilog_epmt.sh" /tmp/sleeptest.bash
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (sh)" {
      srun -n1 --task-prolog="${resource_path}/slurm/slurm_task_prolog_epmt.sh" --task-epilog="${resource_path}/slurm/slurm_task_epilog_epmt.sh" /tmp/sleeptest.sh
      assert_success
      verify_staged_file
      assert_success
}
