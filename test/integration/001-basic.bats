load 'libs/bats-support/load'
load 'libs/bats-assert/load'

@test "epmt version" {
  run epmt -V
  assert_output --regexp '^EPMT [0-9]+\.[0-9]+\.[0-9]+$'
}

setup() {
  command -v epmt
  # if we are running from the source tree
  if [ -f epmt_cmds.py ]; then
     resource_path=$(dirname `command -v epmt`)
  else # in production/binary release
     resource_path=$(dirname `command -v epmt`)/..
  fi	
  test -n "${resource_path}" || fail
  test -d ${resource_path} || fail
  # Create
  tmp_job_dir=$(mktemp -d)
  # Extract
  tar zxvf ${resource_path}/test/data/submit/804280.tgz -C ${tmp_job_dir}
  jobs_in_module='692500 804280 685000'
}

teardown() {
  rm -rf ${tmp_job_dir}
  # Remove any jobs before starting a test & ignore error code
  epmt delete ${jobs_in_module} || true
}

@test "epmt submit" {
  run epmt submit ${resource_path}/test/data/submit/692500.tgz
  assert_success
  assert_output --partial "Imported successfully - job: 692500 processes: 6486"
}

@test "epmt submit dir" {
  run epmt submit ${tmp_job_dir}/
  assert_success
  assert_output --partial "Imported successfully - job: 804280 processes: 6039"
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
