load 'libs/bats-support/load'
load 'libs/bats-assert/load'


@test "epmt version" {
  run epmt -V
  assert_output --regexp '^EPMT [0-9]+\.[0-9]+\.[0-9]+$'
}

@test "epmt submit -n" {
  if epmt list | grep 692500 > /dev/null; then
      epmt delete 692500
  fi
  epmt submit -n test/data/submit/692500.tgz
  run epmt list 692500
  assert_failure
}

@test "epmt submit" {
  if epmt list | grep 692500 > /dev/null; then
      epmt delete 692500
  fi
  run epmt submit test/data/submit/692500.tgz
  assert_output --partial "Imported successfully - job: 692500 processes: 6486"
}

@test "epmt submit -e" {
  if epmt list | grep 685000 > /dev/null; then
      epmt delete 685000
  fi
  run epmt submit -e test/data/submit/692500.tgz test/data/submit/685000.tgz
  assert_failure
  assert_output --partial "Job already in database: test/data/submit/692500.tgz"
  run epmt list 685000
  assert_failure
}
