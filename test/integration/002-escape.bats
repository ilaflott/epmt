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
  export SLURM_JOB_ID=12340
  epmt start           # Generate prolog
  eval `epmt source`   # Setup environment
  # begin workload
  cut -d\" -f2 < /dev/null
  /bin/echo '\\\'
  /bin/echo \ b
  /bin/echo \\
  /bin/echo ,
  /bin/echo \'
  /bin/echo -e "\tHello"
  /bin/echo -e "\tThereU\nR"
  /bin/echo -e \\\a
  /bin/echo -e "\a"
  /bin/echo -e \\
  /bin/echo -e 'some test \b and more text'
  /bin/echo \b
  /bin/echo \\b
  /bin/echo '\b'
  /bin/echo -e '\. some text'
  /bin/echo -e 'try\.some more text'
  sed 's/^\.//' < /dev/null
  # end workload
  epmt_uninstrument      # disable instrumentation
  epmt stop              # Wrap up job stats
  # f=`epmt stage`       # Move to medium term storage ($PWD)
  run epmt submit --remove  # Submit to DB
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
