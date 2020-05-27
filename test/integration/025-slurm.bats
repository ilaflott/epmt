load 'libs/bats-support/load'
load 'libs/bats-assert/load'

verify_staged_file() {
  local wait_seconds=10
  until test $wait_seconds -eq 0 || ls -t *.tgz 2>&1 >/dev/null ; do sleep 1; (( wait_seconds-- )); done
  tgz=$(ls -t *.tgz | head -n 1)
  test -s $tgz
  tar xf $tgz
  test -s job_metadata
  test -s *-collated-papiex-*-*.csv
  rm -f $tgz job_metadata *-collated-papiex-*-*.csv
  echo "$cmd PASSED"
}

setup() {
#  sinfo || skip
#  sbatch || skip
#  srun || skip
  epmt -V || skip
  install_path=$(dirname `command -v epmt`)
  stage_dest=$(epmt -h | sed -n 's/stage_command_dest://p')
  test -n "${stage_dest}" || fail
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
      sbatch ${install_path}/../examples/epmt-example.tcsh 
      assert_success
      verify_staged_file
      assert_success
}
@test "sbatch epmt-example.csh" {
      sbatch ${install_path}/../examples/epmt-example.csh
      assert_success
      verify_staged_file
      assert_success      
}
@test "sbatch epmt-example.bash" {
      sbatch ${install_path}/../examples/epmt-example.bash
      assert_success
      verify_staged_file
      assert_success
}
@test "sbatch epmt-example.sh" {
      sbatch ${install_path}/../examples/epmt-example.sh
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (inline)" {
      srun -n1 --task-prolog="${install_path}/../slurm/slurm_task_prolog_epmt.sh" --task-epilog="${install_path}/../slurm/slurm_task_epilog_epmt.sh" sleep 1
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (tcsh)" {
      srun -n1 --task-prolog="${install_path}/../slurm/slurm_task_prolog_epmt.sh" --task-epilog="${install_path}/../slurm/slurm_task_epilog_epmt.sh" /tmp/sleeptest.tcsh
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (csh)" {
      srun -n1 --task-prolog="${install_path}/../slurm/slurm_task_prolog_epmt.sh" --task-epilog="${install_path}/../slurm/slurm_task_epilog_epmt.sh" /tmp/sleeptest.csh
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (bash)" {
      srun -n1 --task-prolog="${install_path}/../slurm/slurm_task_prolog_epmt.sh" --task-epilog="${install_path}/../slurm/slurm_task_epilog_epmt.sh" /tmp/sleeptest.bash
      assert_success
      verify_staged_file
      assert_success
}
@test "srun prolog/epilog (sh)" {
      srun -n1 --task-prolog="${install_path}/../slurm/slurm_task_prolog_epmt.sh" --task-epilog="${install_path}/../slurm/slurm_task_epilog_epmt.sh" /tmp/sleeptest.sh
      assert_success
      verify_staged_file
      assert_success
}
