load 'libs/bats-support/load'
load 'libs/bats-assert/load'

setup() {
  resource_path=$(dirname `command -v epmt`)
  test -n "${resource_path}" || fail
  test -d ${resource_path} || fail

  jobs_in_module='625151 627907 629322 633114 675992 680163 685000 685001 685003 685016 691209 692500 693129'
  epmt delete ${jobs_in_module} || true
  epmt submit ${resource_path}/test/data/submit/692500.tgz ${resource_path}/test/data/query/*.tgz ${resource_path}/test/data/outliers_nb/{625151,627907,629322,633114,675992,680163,685001,691209,693129}.tgz
  epmt dump ${jobs_in_module} > /dev/null # force PP
}
teardown() {
  epmt delete ${jobs_in_module} || true
}

@test "epmt explore (can take a couple of minutes)" {
  # Skip this test if using in-memory SQLite database
  db_params=$(epmt -h | grep db_params:| cut -f2- -d:)
  [[ "$db_params" =~ ":memory:" ]] && skip "Test requires persistent database, skipping for in-memory SQLite"

  run epmt explore ESM4_historical_D151
  # assert_output --partial "Experiment ESM4_historical_D151 contains 13 jobs: 625151,627907,629322,633114,675992,680163,685000..685001,685003,685016,691209,692500,693129"
  assert_output --partial "ocean_annual_z_1     18540101       625151      10425623185   ****"
  assert_output --partial "ocean_annual_z_1     18590101       627907       6589174875"
  assert_output --partial "ocean_annual_z_1     18890101       691209        860163243   ****"
  assert_output --partial "ocean_annual_z_1     18940101       693129       3619324767     **"
  assert_output --partial "18540101      10425623185"
  assert_output --partial "18840101      26897098077   ****"
}

