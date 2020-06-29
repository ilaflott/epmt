load 'libs/bats-support/load'
load 'libs/bats-assert/load'

setup(){
  stage_dest=$(epmt -h | sed -n 's/stage_command_dest://p')
  test -n "${stage_dest}" || fail
  test -d ${stage_dest} || fail
  jobs_in_module='989'
  rm -f ${stage_dest}/989.tgz
  epmt delete ${jobs_in_module} || true
  
}
teardown() {
  epmt delete ${jobs_in_module} || true
  rm -f ${stage_dest}/989.tgz
}

@test "epmt with COLLATED_TSV" {
  # orm=$(epmt -h | grep orm:| cut -f2 -d:)
  # [[ $orm == "sqlalchemy" ]] || skip
  # db_params=$(epmt -h | grep db_params:| cut -f2- -d:)
  # [[ "$db_params" =~ "postgres" ]] || skip

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
  # lets see if we have fixed the bug wherein calling
  # get_procs prior to post-processing a job would return no
  # processes
  run epmt list procs jobs=$jobid limit=1
  assert_success
  run epmt dump -k tags $jobid 
  assert_output "{'op': 'check-tsv'}"
  run test -f ${stage_dest}/989.tgz || fail
  assert_success
  rm -f ${stage_dest}/989.tgz
}
