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
} 

teardown() {
  rm -rf ${epmt_output_prefix}/${USER}/3456
  rm -f ${stage_dest}/3456.tgz
} 

@test "epmt annotate" {
  run ${resource_path}/test/integration/epmt-annotate.sh
  assert_success
  run test -f ${stage_dest}/3456.tgz
  assert_success
  run epmt dump -k annotations ${stage_dest}/3456.tgz
  assert_success
  
  # the order of keys in the dict might change based on underlying db
  assert_output "{'a': 100, 'b': 200, 'inbetween_1': 1, 'inbetween_2': 1, 'c': 200, 'd': 400, 'e': 300, 'f': 600}"

  # the last test only works with a persistent db
  if  epmt help| grep db_params| grep postgres > /dev/null; then
      epmt annotate 3456 g=400 h=800  # annotate job in database as well
      run epmt dump -k annotations 3456
      assert_output "{'a': 100, 'b': 200, 'c': 200, 'd': 400, 'e': 300, 'f': 600, 'g': 400, 'h': 800, 'inbetween_1': 1, 'inbetween_2': 1}"
      # special annotation, check we set the tags field
      epmt annotate 3456 EPMT_JOB_TAGS='exp_name:abc;exp_component:def;exp_time:18540101'
      run epmt dump -k tags 3456
      assert_output "{'exp_name': 'abc', 'exp_time': '18540101', 'exp_component': 'def'}"
  fi
}

