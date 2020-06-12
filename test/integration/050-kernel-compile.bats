load 'libs/bats-support/load'
load 'libs/bats-assert/load'


setup_file(){
  stage_dest=$(epmt -h | sed -n 's/stage_command_dest://p')
  test -n "${stage_dest}" || fail
  test -d ${stage_dest} || fail
  rm -f ${stage_dest}/988.tgz
  jobs_in_module = "988 kernel_build CSV_v1 kernel_build COLLATED_TSV"
  epmt delete ${jobs_in_module} || true
}
teardown_file() {
  jobs_in_module = "988 kernel_build CSV_v1 kernel_build COLLATED_TSV"
  epmt delete ${jobs_in_module} || true
}

# the actual compile step
# you will need the following deps installed:
#   sudo apt-get install build-essential libncurses-dev bison flex libssl-dev libelf-dev coreutils
function _compile() {
    build_dir=$(tempfile -p epmt_ -s _kernel)
    echo "creating build directory: $build_dir"
    rm -rf $build_dir; mkdir -p $build_dir && cd $build_dir
    
    # download
    PAPIEX_TAGS="op:download;op_instance:1;op_sequence:1" wget https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.1.7.tar.xz
    PAPIEX_TAGS="op:untar;op_instance:1;op_sequence:1" tar -xf linux-5.1.7.tar.xz
    cd linux-5.1.7
    
    # configure
    # cp -v /boot/config-$(uname -r) .config
    PAPIEX_TAGS="op:configure;op_instance:1;op_sequence:1" make tinyconfig
    
    # build
    PAPIEX_TAGS="op:compile;op_instance:1;op_sequence:1" make -j $(nproc)

    # cleanup
    PAPIEX_TAGS="op:rm;op_instance:1;op_sequence:1" rm -rf $build_dir
}

function kernel_build() {
  opt=$1
  jobid=988
  export SLURM_JOB_ID=$jobid
  export EPMT_JOB_TAGS="exp_name:kernel_build;papiex_options:$opt"
  epmt start           # Generate prolog
  # set up environment while forcing PAPIEX_OPTIONS to include the opt argument
  if [ "$opt" == "CSV_v1" ]; then
      eval `epmt source| sed '/^PAPIEX_OPTIONS/ s/COLLATED_TSV//'`
  else
      eval `epmt source| sed '/^PAPIEX_OPTIONS/ s/PAPIEX_OPTIONS=/PAPIEX_OPTIONS='$opt',/'`
  fi

  # workload
  (_compile > /dev/null 2>&1)

  epmt_uninstrument    # disable instrumentation
  epmt stop            # Wrap up job stats
  f=`epmt stage`       # Move to medium term storage ($PWD)
  run tar tzf ./$jobid.tgz
  assert_output --partial job_metadata
  run epmt submit $f > /dev/null      # Submit to DB
  assert_output --partial "Imported successfully"
  assert_output --partial "processes: 10602"
  run epmt list
  assert_output --partial $jobid
  run epmt dump -k tags $jobid
  assert_output "{'exp_name': 'kernel_build', 'papiex_options': '"$opt"'}"
  echo $jobid
}

@test "kernel compile with CSV_v1" {
  skip
  jobid=`kernel_build CSV_v1`
  run tar tzf ./$jobid.tgz
  assert_output --partial -collated-
  rm -f $jobid.tgz
}

@test "kernel compile with COLLATED_TSV" {
  skip
  # the test only works with a persistent db
  if  epmt help| grep db_params| grep -w memory > /dev/null; then
      skip
  fi

  # orm=$(epmt -h | grep orm:| cut -f2 -d:)
  # [[ $orm == "sqlalchemy" ]] || skip
  # db_params=$(epmt -h | grep db_params:| cut -f2- -d:)
  # [[ "$db_params" =~ "postgres" ]] || skip

  jobid=`kernel_build COLLATED_TSV`
  run tar tzf ./$jobid.tgz
  assert_output --partial papiex.tsv
  assert_output --partial papiex-header.tsv
  rm -f $jobid.tgz
}
