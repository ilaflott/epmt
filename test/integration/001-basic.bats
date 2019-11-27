load 'libs/bats-support/load'
load 'libs/bats-assert/load'

@test "epmt version" {
  run epmt -V
  assert_output --regexp '^EPMT [0-9]+\.[0-9]+\.[0-9]$'
}

@test "epmt submit" {
  run epmt submit test/data/submit/692500.tgz
  assert_output --partial "Imported successfully - job: 692500 processes: 6486"
}
