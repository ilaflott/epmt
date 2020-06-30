load 'libs/bats-support/load'
load 'libs/bats-assert/load'

@test "epmt version" {
  run epmt -V
  assert_output --regexp '^EPMT [0-9]+\.[0-9]+\.[0-9]+$'
}

setup() {
  resource_path=$(dirname `command -v epmt`)
  test -n "${resource_path}" || fail
  test -d ${resource_path} || fail
  epmt_output_prefix=$(epmt -h | sed -n 's/epmt_output_prefix://p')
  test -n "${epmt_output_prefix}" || fail
  epmt_output_prefix=${epmt_output_prefix}/`whoami`
  test -n "${epmt_output_prefix}" || fail
  jobs_in_module='692500 804280 685000'
  rm -rf ${epmt_output_prefix}/[12]
}

teardown() {
  # Remove any jobs before starting a test & ignore error code
  epmt delete ${jobs_in_module} || true
  rm -rf ${epmt_output_prefix}/[12]
}

@test "epmt start" {
 SLURM_JOB_ID=1 run epmt start -e
 assert_success
 SLURM_JOB_ID=1 run epmt start -e
 assert_failure
 SLURM_JOB_ID=1 run epmt start
 assert_success
}

@test "epmt stop" {
 SLURM_JOB_ID=2 run epmt start -e
 assert_success
 SLURM_JOB_ID=2 run epmt stop -e
 assert_success
 SLURM_JOB_ID=2 run epmt stop -e
 assert_failure
 SLURM_JOB_ID=2 run epmt stop
 assert_success
}

@test "epmt submit" {
  run epmt submit ${resource_path}/test/data/submit/692500.tgz
  assert_success
  assert_output --partial "Imported successfully - job: 692500 processes: 6486"
}

@test "epmt submit dir" {
  tmp_job_dir=$(mktemp -d)
  # Extract
  tar zxvf ${resource_path}/test/data/submit/804280.tgz -C ${tmp_job_dir}
  run epmt submit ${tmp_job_dir}/
  assert_success
  assert_output --partial "Imported successfully - job: 804280 processes: 6039"
  rm -rf ${tmp_job_dir}
}

@test "epmt submit -e" {
  run epmt submit -e ${resource_path}/test/data/submit/692500.tgz
  run epmt submit -e ${resource_path}/test/data/submit/692500.tgz ${resource_path}/test/data/query/685000.tgz
  assert_failure
  assert_output --partial "Job already in database:"
  # Path may not be exact
  assert_output --partial "test/data/submit/692500.tgz"
  run epmt list 685000
  assert_output "[]"
}
