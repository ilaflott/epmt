load 'libs/bats-support/load'
load 'libs/bats-assert/load'

@test "epmt annotate" {
  run test/integration/epmt-annotate.sh
  run test -f 3456.tgz
  run epmt dump 3456.tgz
  assert_output --partial "job_annotations         {'a': 100, 'b': 200, 'c': 200, 'd': 400, 'e': 300, 'f': 600}"
  run epmt show 3456
  assert_output --partial "annotations               {'a': 100, 'b': 200, 'c': 200, 'd': 400, 'e': 300, 'f': 600, 'g': 400, 'h': 800}"
}

