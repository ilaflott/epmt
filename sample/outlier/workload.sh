#!/bin/bash -e

njobs=${1:-1}
export TMPDIR=${TMPDIR:-"/tmp"}
job_prefix="kern-bld-$$"

function work_unit() {
    jobid="${job_prefix}-$(date +%Y%m%d-%H%M%S)"
    rm -rf ./$jobid $TMPDIR/epmt/$jobid ./$jobid.tgz
    echo "  - starting job $jobid"
    export EPMT_JOB_TAGS="exp_name:linux_kernel;exp_component:kernel_tiny;launch_id=$$;seqno$1"

    epmt -j$jobid start           # Generate prolog
    eval `epmt -j$jobid source`   # Setup environment
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

    unset LD_PRELOAD
    epmt -j$jobid stop            # Generate epilog and append
    echo "  - staging $jobid (to ./$jobid.tgz)"
    epmt -j$jobid stage           # Move to medium term storage
    echo "  - submitting $jobid (from ./$jobid.tgz)"
    epmt submit ./$jobid.tgz      # Submit from staged storage
    rm -f ./$jobid.tgz
}

echo "Workload consists of $njobs jobs"
echo "Launch ID: $$"

for n in `seq 1 $njobs`; do
    echo "job $n"
    work_unit $n
done
