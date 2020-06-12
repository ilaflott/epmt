load 'libs/bats-support/load'
load 'libs/bats-assert/load'

setup(){
  stage_dest=$(epmt -h | sed -n 's/stage_command_dest://p')
  test -n "${stage_dest}" || fail
  test -d ${stage_dest} || fail
  rm -f ${stage_dest}/989.tgz
  epmt delete 989 || true
}

@test "epmt with COLLATED_TSV" {

  jobid=989
  export SLURM_JOB_ID=$jobid
  export EPMT_JOB_TAGS='op:check-tsv'
  epmt start           # Generate prolog
  # set up environment while forcing PAPIEX_OPTIONS to include COLLATED_TSV
  eval `epmt source| sed '/^PAPIEX_OPTIONS/ s/PAPIEX_OPTIONS=/PAPIEX_OPTIONS=COLLATED_TSV,/'`
  /bin/sleep 1 2>/dev/null >&2 # Workload
  epmt_uninstrument    # End Workload, disable instrumentation
  epmt stop            # Wrap up job stats
  f=`epmt stage`       # Move to medium term storage ($PWD)
  epmt -v submit $f       # Submit to DB
  epmt list | grep -w $jobid > /dev/null
  run epmt dump -k tags $jobid 
  assert_output "{'op': 'check-tsv'}"
  run test -f ${stage_dest}/989.tgz || fail
  assert_success
  rm -f ${stage_dest}/989.tgz
}
