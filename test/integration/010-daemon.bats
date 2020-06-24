load 'libs/bats-support/load'
load 'libs/bats-assert/load'

function sig_handler() {
  echo "Cleaning up daemons.."
  # we run in a loop for a few seconds, as sometimes
  # epmt daemon --start takes a couple of seconds before
  # it has the lockfile in place
  for i in 1 2 3 4 5; do
    epmt daemon --stop > /dev/null 2>&1 && return
    sleep 1
  done
}

setup() {
  jobs=$(epmt list processed=0)
}

@test "no daemon running" {
  # skip test if we have any unprocessed jobs
  [[ "$jobs" == "[]" ]] || skip
  run epmt daemon
  assert_output --partial "EPMT daemon is not running"
}

@test "start epmt daemon" {
  # skip test if we have any unprocessed jobs
  [[ "$jobs" == "[]" ]] || skip
  trap sig_handler SIGINT SIGTERM SIGQUIT SIGHUP
  run epmt daemon --start
  run epmt daemon
  assert_output --partial "EPMT daemon running OK"
}


@test "stop epmt daemon" {
  # skip test if we have any unprocessed jobs
  [[ "$jobs" == "[]" ]] || skip
  run epmt daemon
  assert_output --partial "EPMT daemon running OK"
  run epmt daemon --stop
  assert_output --partial "Sending signal to EPMT daemon with PID"
}
