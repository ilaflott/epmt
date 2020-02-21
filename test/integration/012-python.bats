load 'libs/bats-support/load'
load 'libs/bats-assert/load'


@test "epmt shell" {
  run epmt shell < /dev/null
  assert_output --partial ">>>"
  assert_output --partial "now exiting InteractiveConsole..."

  echo help | epmt shell | grep ">>> <pydoc.Helper instance>" > /dev/null
}


@test "epmt python" {
  echo -e "from sys import version_info\nprint(version_info)" | epmt python - | grep "sys.version_info(major=3"
}
