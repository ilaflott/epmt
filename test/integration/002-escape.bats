load 'libs/bats-support/load'
load 'libs/bats-assert/load'

setup() {
  resource_path=$(dirname `command -v epmt`)
  test -n "${resource_path}" || fail
  test -d ${resource_path} || fail
  jobs_in_module='12340'
  cleanup
}

teardown() {
  cleanup
}

cleanup() {
  # Remove any jobs before starting a test & ignore error code
  epmt delete ${jobs_in_module} || true
}

@test "epmt submit with escape char" {
  run epmt submit "${resource_path}"/test/data/tsv/12340
  assert_success
  assert_output --partial "Imported successfully - job: 12340 processes: 18"
  run epmt list 12340
  assert_success
  assert_output "['12340']"
  epmt dump -k info_dict 12340 # to trigger post-processing
  # remember python will escape every backslash in a string
  # so, while the database will have raw string, when we print it out
  # we will be getting escaped backslashes. So, adjust the expected
  # output accordingly.
  exp_output=('-d" -f2' '\\\\\\' ' b' '\\' ',' "'" '-e \\tHello' '-e \\tThereU\\nR' '-e \\a' '-e \\a' '-e \\' '-e some test \\b and more text' 'b' '\\b' '\\b' '-e \\. some text' '-e try\\.some more text' 's/^\\.//')
  for i in ${!exp_output[*]}; do
      run epmt list procs jobs=12340 limit=1 offset=$i
      assert_output --partial "${exp_output[$i]}"
  done
}
