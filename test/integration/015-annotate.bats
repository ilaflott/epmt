load 'libs/bats-support/load'
load 'libs/bats-assert/load'

setup() {
  stage_dest=$(epmt -h | sed -n 's/stage_command_dest://p')
  test -n "${stage_dest}" || fail
  test -d ${stage_dest} || fail
  resource_path=$(dirname `command -v epmt`)
  test -n "${resource_path}" || fail
  test -d ${resource_path} || fail
  epmt_output_prefix=$(epmt -h | sed -n 's/epmt_output_prefix://p')
  test -n "${epmt_output_prefix}" || fail
  rm -rf ${epmt_output_prefix}/${USER}/3456
  rm -f ${stage_dest}/3456.tgz
  run epmt delete 3456
  run ${resource_path}/test/integration/epmt-annotate.sh || fail
  run test -f ${stage_dest}/3456.tgz || fail
} 

teardown() {
  rm -rf ${epmt_output_prefix}/${USER}/3456
  rm -f ${stage_dest}/3456.tgz
  epmt delete 3456 || true
} 

@test "epmt annotate read tgz" {
  run epmt dump -k annotations ${stage_dest}/3456.tgz
  assert_success
  # the order of keys in the dict might change based on underlying db
  assert_output --partial "'a': 100, 'b': 200"
  assert_output --partial "'inbetween_1': 1, 'inbetween_2': 1"
  assert_output --partial "'c': 200, 'd': 400, 'e': 300, 'f': 600"
}
@test "epmt annotate write db" {
    # requires a persistant backend
  if epmt -h | grep db_params | grep -w memory; then
      skip
  fi

  epmt annotate 3456 g=400 h=800  # annotate job in database as well
  run epmt dump -k annotations 3456
  assert_output --partial "'c': 200, 'd': 400, 'e': 300, 'f': 600"
  assert_output --partial "'g': 400, 'h': 800"
  # special annotation, check we set the tags field
  epmt annotate 3456 EPMT_JOB_TAGS='exp_name:abc;exp_component:def;exp_time:18540101'
  run epmt dump -k tags 3456
  assert_output --partial "'exp_name': 'abc'"
  assert_output --partial "'exp_component': 'def'"
  assert_output --partial "'exp_time': '18540101'"
}

# Replace is used on setting state on all tests
# Be sure it works well
@test "epmt annotate replace" {
    # requires a persistant backend
  if epmt -h | grep db_params | grep -w memory; then
      skip
  fi

  # first set and verify known tags state
  run epmt annotate --replace 3456 a=100 EPMT_JOB_TAGS="jobid:3456"
  assert_success
  run epmt dump -k tags 3456
  assert_success
  assert_output "{'jobid': '3456'}"
  # Tags with backslash
  run epmt annotate --replace 3456 a=200
  assert_success
  run epmt dump -k annotations 3456
  assert_success
  # Note 1 escaped backslash is dropped in the test
  # This appears tested as {'\\test': '\\hello'}
  assert_output "{'a': 200}"
}

@test "epmt annotate replace jobtags" {
    # requires a persistant backend
  if epmt -h | grep db_params | grep -w memory; then
      skip
  fi

  # first set and verify known tags state
  run epmt annotate --replace 3456 a=100 EPMT_JOB_TAGS="jobid:3456;ocn_res:0.5l75"
  assert_success
  run epmt dump -k tags 3456
  assert_success
  assert_output --partial "'jobid': '3456'"
  assert_output --partial "'ocn_res': '0.5l75'"
  # Tags with backslash
  run epmt annotate --replace 3456 'EPMT_JOB_TAGS'='jobid:123'
  assert_success
  run epmt dump -k tags 3456
  assert_success
  assert_output "{'jobid': '123'}"
}

@test "epmt bad annotate" {
    # requires a persistant backend
  if epmt -h | grep db_params | grep -w memory; then
      skip
  fi

  run epmt annotate abc
  assert_failure
  assert_output --partial "epmt_annotate: form must be"
  run epmt annotate 3456 abc
  assert_failure
  assert_output --partial "epmt_annotate: form must be"
}

@test "epmt annotate incomplete" {
    # requires a persistant backend
  if epmt -h | grep db_params | grep -w memory; then
      skip
  fi

  # first set and verify known annotation state
  run epmt annotate --replace 3456 a=100 EPMT_JOB_TAGS="jobid:3456"
  assert_success
  run epmt dump -k annotations 3456
  assert_success
  assert_output --partial "'a': 100"
  assert_output --partial "'EPMT_JOB_TAGS': 'jobid:3456'"
  
  # Incomplete annotation
  run epmt annotate --replace 3456 'test'=
  assert_failure
  run epmt dump -k annotations 3456
  assert_success
  assert_output --partial "'a': 100"
  assert_output --partial "'EPMT_JOB_TAGS': 'jobid:3456'"
}

@test "epmt annotate tag incomplete" {
  # requires a persistant backend
  if epmt -h | grep db_params | grep -w memory; then
      skip
  fi

  # first set and verify known tag state
  run epmt annotate --replace 3456 a=100 EPMT_JOB_TAGS="jobid:3456"
  assert_success
  run epmt dump -k tags 3456
  assert_success
  assert_output "{'jobid': '3456'}"
  # Incomplete Job tags
  run epmt annotate 3456 'EPMT_JOB_TAGS'=
  assert_failure
  run epmt dump -k tags 3456
  assert_success
  assert_output "{'jobid': '3456'}"
}

@test "epmt annotate backslash" {
  # requires a persistant backend
  if epmt -h | grep db_params | grep -w memory; then
      skip
  fi

  # first set and verify known tags state
  run epmt annotate --replace 3456 a=100 EPMT_JOB_TAGS="jobid:3456"
  assert_success
  run epmt dump -k tags 3456
  assert_success
  assert_output "{'jobid': '3456'}"
  # Tags with backslash
  run epmt annotate --replace 3456 'EPMT_JOB_TAGS'='\test:\hello'
  assert_success
  run epmt dump -k tags 3456
  assert_success
  # Note 1 escaped backslash is dropped in the test
  # This appears tested as {'\\test': '\\hello'}
  assert_output "{'\\\test': '\\\hello'}"
}
