load 'libs/bats-support/load'
load 'libs/bats-assert/load'

setup() {
  # need a persistent db
  if  epmt help| grep db_params| grep -w memory > /dev/null; then
      return 0
  fi
  epmt submit test/data/submit/692500.tgz test/data/query/*.tgz test/data/outliers_nb/{625151,627907,629322,633114,675992,680163,685001,691209,693129}.tgz
}

@test "epmt explore (can take a couple of minutes)" {
  # need a persistent db
  if  epmt help| grep db_params| grep -w memory > /dev/null; then
      skip
  fi
  run epmt explore ESM4_historical_D151
  # assert_output --partial "Experiment ESM4_historical_D151 contains 13 jobs: 625151,627907,629322,633114,675992,680163,685000..685001,685003,685016,691209,692500,693129"
  assert_output --partial "ocean_annual_z_1     18540101       625151      10425623185   ****"
  assert_output --partial "ocean_annual_z_1     18590101       627907       6589174875"
  assert_output --partial "ocean_annual_z_1     18890101       691209        860163243   ****"
  assert_output --partial "ocean_annual_z_1     18940101       693129       3619324767     **"
  assert_output --partial "18540101      10425623185"
  assert_output --partial "18840101      26897098077   ****"
}

