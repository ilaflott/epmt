load 'libs/bats-support/load'
load 'libs/bats-assert/load'

setup() {
  rm -f pp053-collated-papiex-csv-0.csv corrupted_csv.tgz
}

teardown() {
  rm -f pp053-collated-papiex-csv-0.csv corrupted_csv.tgz
}

@test "epmt_concat -h" {
  test -x epmt_concat.py || skip
  run epmt_concat.py -h
  assert_success
  assert_output --partial "Concatenate CSV files"
}

@test "epmt_concat with valid input dir" {
  test -x epmt_concat.py || skip
  run epmt_concat.py test/data/csv/
  assert_success
  run test -f pp053-collated-papiex-csv-0.csv
  assert_success
  run sum pp053-collated-papiex-csv-0.csv
  assert_output --partial "13120"
  #--regexp "13120\s+2"
  #^13120\s+2\s+.*$"
  #"13120     2"
}

@test "epmt_concat with valid input files" {
  test -x epmt_concat.py || skip
  run epmt_concat.py test/data/csv/*.csv
  assert_success
  run test -f pp053-collated-papiex-csv-0.csv
  assert_success
  run sum pp053-collated-papiex-csv-0.csv
  assert_output --partial "13120"
}

@test "epmt_concat with non-existent directory" {
  test -x epmt_concat.py || skip
  run epmt_concat.py x/
  assert_failure
  assert_output --partial "x/ does not exist or is not a directory"
}
@test "epmt_concat with non-existent files" {
  test -x epmt_concat.py || skip
  run epmt_concat.py x.csv y.csv
  assert_failure
  assert_output --partial "does not exist or is not a file"
}

@test "epmt_concat with corrupted csv" {
  test -x epmt_concat.py || skip
  run epmt_concat.py -e test/data/corrupted_csv/
  assert_failure
  assert_output --partial "File: test/data/corrupted_csv/pp053-papiex-615503-0.csv, Header: 40 delimiters, but this row has 39 delimiters"
  # assert_output --partial "ERROR:epmt_concat:Error concatenating files: Different number of elements in header and data in test/data/corrupted_csv/pp053-papiex-615503-0.csv"
}
