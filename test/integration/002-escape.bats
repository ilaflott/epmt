load 'libs/bats-support/load'
load 'libs/bats-assert/load'

setup() {
  resource_path=$(dirname `command -v epmt`)
  papiex_path=$(epmt -h | grep install_prefix|cut -f2 -d:)
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

workload() {
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
}

@test "epmt submit with escape char" {
  # depending on whether we have papiex or not, we will run the workload
  # or load the test output from a saved job
  export SLURM_JOB_ID=12340
  if test -f "${papiex_path}/lib/libpapiex.so"; then
    # we have papiex available
    epmt start           # Generate prolog
    eval `epmt source`   # Setup environment
    workload
    epmt_uninstrument    # End Workload, disable instrumentation
    epmt stop            # Wrap up job stats
    run epmt submit --remove
  else
    # in CI env we don't have papiex so use our stored output
    run epmt submit "${resource_path}"/test/data/tsv/12340
  fi
  unset SLURM_JOB_ID
  assert_success
  assert_output --partial "Imported successfully - job: 12340 processes: 18"
  run epmt list 12340
  assert_success
  assert_output "['12340']"

  # Below we have the expected output in sequence
  exp_output=('-d" -f2' '\\\' ' b' '\' ',' "'" '-e \tHello' '-e \tThereU\nR' '-e \a' '-e \a' '-e \' '-e some test \b and more text' 'b' '\b' '\b' '-e \. some text' '-e try\.some more text' 's/^\.//')

  # don't use run as it doesn't play with a pipe
  for i in ${!exp_output[*]}; do
      out=$(echo 'import epmt_query as eq; procs=eq.get_procs(fmt="orm", jobs=["12340"])[:]; p = procs['$i']; print(p.args);'  | epmt python -)
      [[ "$out" == "${exp_output[$i]}" ]]
  done
}
