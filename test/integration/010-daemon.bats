load 'libs/bats-support/load'
load 'libs/bats-assert/load'

@test "no daemon running" {
  run epmt daemon
  assert_output --partial "EPMT daemon is not running"
}

@test "start epmt daemon" {
  run epmt daemon --start
  run epmt daemon
  assert_output --partial "EPMT daemon running OK"
}


@test "stop epmt daemon" {
  run epmt daemon
  assert_output --partial "EPMT daemon running OK"
  run epmt daemon --stop
  assert_output --partial "Sending signal to EPMT daemon with PID"
}
