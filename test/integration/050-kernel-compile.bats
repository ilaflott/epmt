load 'libs/bats-support/load'
load 'libs/bats-assert/load'

resource_path=$(dirname `command -v epmt`)

function kernel_build() {
  opt=$1
  jobid=$RANDOM
  export SLURM_JOB_ID=$jobid
  export EPMT_JOB_TAGS="exp_name:kernel_build;papiex_options:$opt"
  epmt start           # Generate prolog
  # set up environment while forcing PAPIEX_OPTIONS to include the opt argument
  if [ "$opt" == "" ]; then
      eval `epmt source`
  else
      eval `epmt source| sed '/^PAPIEX_OPTIONS/ s/PAPIEX_OPTIONS=/PAPIEX_OPTIONS='$opt',/'`
  fi
  ${resource_path}/test/integration/kernel_bld.sh >/dev/null 2>&1 # Workload
  epmt_uninstrument    # End Workload, disable instrumentation
  epmt stop            # Wrap up job stats
  f=`epmt stage`       # Move to medium term storage ($PWD)
  epmt submit $f > /dev/null      # Submit to DB
  echo $jobid
}

# this test only works with sqla+postgres
@test "kernel compile with COLLATED_TSV" {
  orm=$(epmt -h | grep orm:| cut -f2 -d:)
  [[ $orm == "sqlalchemy" ]] || skip
  db_params=$(epmt -h | grep db_params:| cut -f2- -d:)
  [[ "$db_params" =~ "postgres" ]] || skip
  jobid=`kernel_build COLLATED_TSV`
  run tar tzf ./$jobid.tgz
  assert_output --partial ./job_metadata
  assert_output --partial papiex.tsv
  assert_output --partial papiex-header.tsv
  run epmt list
  assert_output --partial $jobid
  # run epmt dump -k tags $jobid 
  # assert_output "{'exp_name': 'kernel_build', 'papiex_options': 'COLLATED_TSV'}"
}
