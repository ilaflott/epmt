load 'libs/bats-support/load'
load 'libs/bats-assert/load'

@test "epmt version" {
  run epmt -V
  assert_output --regexp '^EPMT [0-9]+\.[0-9]+\.[0-9]+$'
}

setup() {
  jobs_in_module='692500 804280'
  resource_path=$(dirname `command -v epmt`)/..
  # echo "resource_path:${resource_path}"
  test -n "${resource_path}" || fail
  test -d ${resource_path} || fail
  # Cleanup
  rm -rf  ${resource_path}/epmt/test/data/submit/804280/
  # Create
  tmp_job_dir=$(mktemp -d)
  # Extract
  tar zxvf  ${resource_path}/epmt/test/data/submit/804280.tgz -C ${tmp_job_dir}
}

teardown() {
  rm -rf ${tmp_job_dir}
  # Remove any jobs before starting a test & ignore error code
  epmt delete ${jobs_in_module} || true
}

@test "epmt submit" {
  if epmt list | grep 692500 > /dev/null; then
      epmt delete 692500
  fi
  run epmt submit ${resource_path}/epmt/test/data/submit/692500.tgz
  assert_success
  assert_output --partial "Imported successfully - job: 692500 processes: 6486"
}

@test "epmt submit dir" {
  if epmt list | grep 804280 > /dev/null; then
      epmt delete 804280
  fi
  run epmt submit ${tmp_job_dir}/
  assert_success
  assert_output --partial "Imported successfully - job: 804280 processes: 6039"
  run epmt submit -n ${resource_path}/epmt/test/data/submit/804280/
  assert_success
}
