#!/bin/bash

export TMPDIR=${TMPDIR:-"/tmp"}
job_prefix="kern-$$"

trap "echo cleaning up.. ; killall yes 2>/dev/null; kill $(jobs -p) 2>/dev/null; rm -rf $TMPDIR/epmt_*_build; exit 0" INT QUIT TERM EXIT

function work_unit() {
    jobid="${job_prefix}-$(date +%Y%m%d-%H%M%S)"
    rm -rf ./$jobid $TMPDIR/epmt/$jobid ./$jobid.tgz
    export EPMT_JOB_TAGS="exp_name:linux_kernel;exp_component:kernel_tiny;launch_id:$$;seqno:$1"

    # check if it's an outlier
    if [ "$2" != "" ]; then
        outl="(outlier)"
        echo "  started background compute to generate outlier"
        export EPMT_JOB_TAGS="${EPMT_JOB_TAGS};outlier=1"
        jobid="${jobid}-outlier"
        yes > /dev/null &
        yes > /dev/null &
    else
        outl=""
    fi
    start_time=$(date +%s)
    echo "  - starting job $1: $jobid $outl"
    epmt -j$jobid start           # Generate prolog
    eval `epmt -j$jobid source`   # Setup environment
    ${BASH_ALIASES[epmt_source]}
    ##### Work ######
    (
        build_dir=$(tempfile -p epmt_ -s _build)
        echo "    build in directory: $build_dir"
        rm -rf $build_dir; mkdir -p $build_dir && cd $build_dir
        
        # download
        PAPIEX_TAGS="op:download;op_instance:1;op_sequence:1" wget https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.1.7.tar.xz > /dev/null 2>&1
        PAPIEX_TAGS="op:extract;op_instance:2;op_sequence:2" tar -xf linux-5.1.7.tar.xz
        cd linux-5.1.7
        
        # configure
        # cp -v /boot/config-$(uname -r) .config
        PAPIEX_TAGS="op:configure;op_instance:3;op_sequence:3" make tinyconfig > /dev/null 2>&1
        
        # build
        PAPIEX_TAGS="op:build;op_instance:4;op_sequence:4" make > /dev/null 2>&1

        PAPIEX_TAGS="op:clean;op_instance:5;op_sequence:5" rm -rf $build_dir
    )
    #### End work ####

    ${BASH_ALIASES[epmt_unsource]}
    epmt -j$jobid stop            # Generate epilog and append
    end_time=$(date +%s)
    duration=$(expr $end_time - $start_time)
    if [ "$outl" != "" ]; then
        echo "  removing background compute.."
        killall yes 2>/dev/null
    fi
    echo "  - job took approx. $duration seconds"
    echo "  - staging $jobid -> ./$jobid.tgz"
    epmt -j$jobid stage           # Move to medium term storage
    if [ "$submit" != "" ]; then
        echo "  - submitting ./$jobid.tgz"
        epmt submit ./$jobid.tgz      # Submit from staged storage
    fi
    # rm -f ./$jobid.tgz
}

usage="
`basename $0` [-h] [-s] [-o <job-number-to-make-outlier] [-n num_jobs]

e.g.,
To run a workload of 10 jobs and make every fifth job an outlier, do:

`basename $0` -n 10 -o 5

This will create .tgz files in the working directory. If you also
want to submit the jobs after staging, use the -s flag.
"

# parse arguments
while getopts "hn:o:s" opt; do
    case $opt in
      h) echo "$usage"; exit 0;;
      n) njobs=$OPTARG ;;
      o) ojobs=$OPTARG ;;
      s) submit=1 ;;
      \?) echo "$usage"; exit 1;;  # Handle error: unknown option or missing required argument.
    esac
done

if [ "$njobs" == "" ]; then
    echo "$usage"
    exit 1
fi

echo "Workload consists of $njobs jobs"
[ "$submit" == "" ] || echo "Jobs will be submitted after staging"
if [ "$ojobs" != "" ]; then
    echo "Every multiple of $ojobs will be an outlier job"
    outlier=$ojobs
fi
echo "Launch ID: $$"

for n in `seq 1 $njobs`; do
    echo "job $n"
    if [ "$ojobs" != "" ]; then
        if [ "$outlier" -eq $n ]; then
            work_unit $n 1
            outlier=`expr $outlier + $n`
            continue
        fi
        work_unit $n
    fi
done
