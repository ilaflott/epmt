load 'libs/bats-support/load'
load 'libs/bats-assert/load'


@test "epmt python" {
  run epmt python < /dev/null
  assert_output --partial ">>>"
  assert_output --partial "now exiting InteractiveConsole..."

  # echo help | epmt python | grep ">>> <pydoc.Helper instance>" > /dev/null
}


@test "epmt python <script>" {
  echo 'print("Hello World")'| epmt python - | grep "Hello World" > /dev/null
}

# need a test here for epmt python of a file that imports local modules from CWD

# need a test here that imports modules from a PYTHONPATH
