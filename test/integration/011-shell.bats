load 'libs/bats-support/load'
load 'libs/bats-assert/load'


@test "epmt shell" {
  run epmt shell < /dev/null
  assert_output --partial "IPython"
  assert_output --partial "In [1]:"
}

