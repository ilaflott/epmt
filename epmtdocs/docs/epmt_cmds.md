## epmt check

Check will verify basic epmt configuration and functionality.

## epmt source

Source provides commands to begin automatic performance instrumentation of all
subsequent shell commands. Standard use of this is via the shell's eval method
inside job scripts or batch system wrappers. For example:

        eval `epmt source` in Bash or Csh
        eval `epmt source --slurm` for a SLURM prolog.

Two shell functions/aliases are created to pause/restart instrumentation:

        epmt_uninstrument - to pause automatic instrumentation
        epmt_instrument - to renable automatic instruction.

**SLURM USERS NOTE** Use in SLURM's prolog, requires a special syntax
enabled here with the -s or --slurm option. For more info, see:
https://slurm.schedmd.com/prolog_epilog.html

## epmt start

Start will create a metadata log file with the current environment variables.


## epmt run

Run will execute a command in the shell, typically used with the auto -a flag
to perform metadata collection before and after instrumentation.

## epmt stop

Stop will append to the metadata log file with the environment variables at
stop time.

## epmt stage

Stage will compress job or job directories into tgz files for midterm storage
then remove original job files and job directory.

Stage optional arguments:

-e, --error

Stage will exit at the first sign of trouble

--no-collate

Do not collate the files

--no-compress-and-tar

Don't compress and tar the output

## epmt submit

Submit accepts job directories and updates the database configured with
directories given. When run with -n submit will not touch the database and
displays the commands leading up to submission.

## epmt dump

Information about a job

The EPMT Dump command will return all metadata about a job, job username, job tags job exit code all can be found 
here.  This command can be run on job archives, a job in the database or directly a job_metadata file.

### Dump Job metadata from Archive
```
epmt$ epmt dump sample/ppr-batch-sow3/1909/2587750.tgz 
checked                 True                                                    
job_el_env              {'TERM': 'linux', 'HOME': '/home/Jeffrey.Durachta', 'SHELL': '/bin/tcsh', 'USER': 'Jeffrey.Durachta', 'LOGNAME': 'Jeffrey.Durachta', 'PATH': '/home/gfdl/bin2:/usr/local/bin:/bin:/usr/bin:.', 'HOSTTYPE': 'x86_64-linux', 'VENDOR': 'unknown', 'OSTYPE': 'linux', 'MACHTYPE': 'x86_64', 'SHLVL': '2', 'PWD': '/vftmp/Jeffrey.Durachta/job2587750', 'GROUP': 'f', 'HOST': 'pp063', 'LANG': 'en_US', 'LC_TIME': 'C', 'MANPATH': '/home/gfdl/man:/usr/local/man:/usr/share/man', 'OMP_NUM_THREADS': '1', 'ARCHIVE': '/archive/Jeffrey.Durachta', 'MODULE_VERSION': '3.2.10', 'MODULE_VERSION_STACK': '3.2.10', 'MODULESHOME': '/usr/local/Modules/3.2.10', 'MODULEPATH': '/usr/local/Modules/modulefiles:/home/fms/local/modulefiles', 'LOADEDMODULES': '', 'SLURM_JOB_NAME': 'ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101', 'SLURM_PRIO_PROCESS': '0', 'SLURM_SUBMIT_DIR': '/home/Jeffrey.Durachta/CMIP6/ESM4/AerChemMIP/ESM4_hist-piAer_D1/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess', 'SLURM_SUBMIT_HOST': 'an107', 'SLURM_GET_USER_ENV': '1', 'SLURM_NPROCS': '1', 'SLURM_NTASKS': '1', 'SLURM_CLUSTER_NAME': 'gfdl', 'SLURM_JOB_ID': '2587750', 'SLURM_JOB_NUM_NODES': '1', 'SLURM_JOB_NODELIST': 'pp063', 'SLURM_JOB_PARTITION': 'batch', 'SLURM_NODE_ALIASES': '(null)', 'SLURM_JOB_CPUS_PER_NODE': '1', 'ENVIRONMENT': 'BATCH', 'HOSTNAME': 'pp063', 'SLURM_JOBID': '2587750', 'SLURM_NNODES': '1', 'SLURM_NODELIST': 'pp063', 'SLURM_TASKS_PER_NODE': '1', 'SLURM_JOB_ACCOUNT': 'gfdl_f', 'SLURM_JOB_QOS': 'Added as default', 'SLURM_TOPOLOGY_ADDR': 'pp063', 'SLURM_TOPOLOGY_ADDR_PATTERN': 'node', 'SLURM_CPUS_ON_NODE': '1', 'SLURM_TASK_PID': '2834', 'SLURM_NODEID': '0', 'SLURM_PROCID': '0', 'SLURM_LOCALID': '0', 'SLURM_GTIDS': '0', 'SLURM_CHECKPOINT_IMAGE_DIR': '/var/slurm/checkpoint', 'SLURM_JOB_UID': '4067', 'SLURM_JOB_USER': 'Jeffrey.Durachta', 'SLURM_WORKING_CLUSTER': 'gfdl:slurm01:6817:8448', 'SLURM_JOB_GID': '70', 'SLURMD_NODENAME': 'pp063', 'TMPDIR': '/vftmp/Jeffrey.Durachta/job2587750', 'TMP': '/vftmp/Jeffrey.Durachta/job2587750', 'JOB_ID': '2587750', 'EPMT_JOB_TAGS': 'exp_name:ESM4_hist-piAer_D1;exp_component:ocean_cobalt_sfc;exp_time:19090101;atm_res:c96l49;ocn_res:0.5l75;script_name:ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101', 'jobname': 'ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101', 'EPMT_PREFIX': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6', 'EPMT_PATH': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6/epmt-install/epmt', 'EPMT': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6/epmt-install/epmt/epmt', 'pp_script': '/home/Jeffrey.Durachta/CMIP6/ESM4/AerChemMIP/ESM4_hist-piAer_D1/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101.tags', 'LD_LIBRARY_PATH': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6/epmt-install/epmt', 'MPLCONFIGDIR': '/vftmp/Jeffrey.Durachta/job2587750/tmpvikl5v1b', 'MATPLOTLIBDATA': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6/epmt-install/epmt/mpl-data'}
job_el_exitcode         0                                                       
job_el_reason           none                                                    
job_el_stop_ts          2019-12-31 11:53:42.706188-05:00                        
job_env_changes         {'MPLCONFIGDIR': '/vftmp/Jeffrey.Durachta/job2587750/tmpvikl5v1b'}
job_jobname             ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101            
job_pl_env              {'TERM': 'linux', 'HOME': '/home/Jeffrey.Durachta', 'SHELL': '/bin/tcsh', 'USER': 'Jeffrey.Durachta', 'LOGNAME': 'Jeffrey.Durachta', 'PATH': '/home/gfdl/bin2:/usr/local/bin:/bin:/usr/bin:.', 'HOSTTYPE': 'x86_64-linux', 'VENDOR': 'unknown', 'OSTYPE': 'linux', 'MACHTYPE': 'x86_64', 'SHLVL': '2', 'PWD': '/vftmp/Jeffrey.Durachta/job2587750', 'GROUP': 'f', 'HOST': 'pp063', 'LANG': 'en_US', 'LC_TIME': 'C', 'MANPATH': '/home/gfdl/man:/usr/local/man:/usr/share/man', 'OMP_NUM_THREADS': '1', 'ARCHIVE': '/archive/Jeffrey.Durachta', 'MODULE_VERSION': '3.2.10', 'MODULE_VERSION_STACK': '3.2.10', 'MODULESHOME': '/usr/local/Modules/3.2.10', 'MODULEPATH': '/usr/local/Modules/modulefiles:/home/fms/local/modulefiles', 'LOADEDMODULES': '', 'SLURM_JOB_NAME': 'ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101', 'SLURM_PRIO_PROCESS': '0', 'SLURM_SUBMIT_DIR': '/home/Jeffrey.Durachta/CMIP6/ESM4/AerChemMIP/ESM4_hist-piAer_D1/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess', 'SLURM_SUBMIT_HOST': 'an107', 'SLURM_GET_USER_ENV': '1', 'SLURM_NPROCS': '1', 'SLURM_NTASKS': '1', 'SLURM_CLUSTER_NAME': 'gfdl', 'SLURM_JOB_ID': '2587750', 'SLURM_JOB_NUM_NODES': '1', 'SLURM_JOB_NODELIST': 'pp063', 'SLURM_JOB_PARTITION': 'batch', 'SLURM_NODE_ALIASES': '(null)', 'SLURM_JOB_CPUS_PER_NODE': '1', 'ENVIRONMENT': 'BATCH', 'HOSTNAME': 'pp063', 'SLURM_JOBID': '2587750', 'SLURM_NNODES': '1', 'SLURM_NODELIST': 'pp063', 'SLURM_TASKS_PER_NODE': '1', 'SLURM_JOB_ACCOUNT': 'gfdl_f', 'SLURM_JOB_QOS': 'Added as default', 'SLURM_TOPOLOGY_ADDR': 'pp063', 'SLURM_TOPOLOGY_ADDR_PATTERN': 'node', 'SLURM_CPUS_ON_NODE': '1', 'SLURM_TASK_PID': '2834', 'SLURM_NODEID': '0', 'SLURM_PROCID': '0', 'SLURM_LOCALID': '0', 'SLURM_GTIDS': '0', 'SLURM_CHECKPOINT_IMAGE_DIR': '/var/slurm/checkpoint', 'SLURM_JOB_UID': '4067', 'SLURM_JOB_USER': 'Jeffrey.Durachta', 'SLURM_WORKING_CLUSTER': 'gfdl:slurm01:6817:8448', 'SLURM_JOB_GID': '70', 'SLURMD_NODENAME': 'pp063', 'TMPDIR': '/vftmp/Jeffrey.Durachta/job2587750', 'TMP': '/vftmp/Jeffrey.Durachta/job2587750', 'JOB_ID': '2587750', 'EPMT_JOB_TAGS': 'exp_name:ESM4_hist-piAer_D1;exp_component:ocean_cobalt_sfc;exp_time:19090101;atm_res:c96l49;ocn_res:0.5l75;script_name:ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101', 'jobname': 'ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101', 'EPMT_PREFIX': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6', 'EPMT_PATH': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6/epmt-install/epmt', 'EPMT': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6/epmt-install/epmt/epmt', 'pp_script': '/home/Jeffrey.Durachta/CMIP6/ESM4/AerChemMIP/ESM4_hist-piAer_D1/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101.tags', 'LD_LIBRARY_PATH': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6/epmt-install/epmt', 'MPLCONFIGDIR': '/vftmp/Jeffrey.Durachta/job2587750/tmp25gxk8ff', 'MATPLOTLIBDATA': '/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.2-centos-6/epmt-install/epmt/mpl-data'}
job_pl_id               2587750                                                 
job_pl_start_ts         2019-12-31 07:54:06.222683-05:00                        
job_pl_submit_ts        2019-12-31 07:54:06.222683-05:00                        
job_pl_username         Jeffrey.Durachta                                        
job_tags                {'exp_name': 'ESM4_hist-piAer_D1', 'exp_component': 'ocean_cobalt_sfc', 'exp_time': '19090101', 'atm_res': 'c96l49', 'ocn_res': '0.5l75', 'script_name': 'ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101'}
```

### Dump Job metadata in database
```
./epmt dump 4899590 
PERF_COUNT_SW_CPU_CLOCK      294801284824        
all_proc_tags             [{'op': 'cp', 'op_instance': '3'}, {'op': 'dmput', 'op_instance': '2'}, {'op': 'fregrid', 'op_instance': '2'}, {'op': 'hsmget', 'op_instance': '1'}, {'op': 'hsmget', 'op_instance': '3'}, {'op': 'hsmget', 'op_instance': '4'}, {'op': 'hsmget', 'op_instance': '6'}, {'op': 'hsmget', 'op_instance': '7'}, {'op': 'mv', 'op_instance': '1'}, {'op': 'mv', 'op_instance': '3'}, {'op': 'ncatted', 'op_instance': '4'}, {'op': 'ncrcat', 'op_instance': '1'}, {'op': 'rm', 'op_instance': '1'}, {'op': 'rm', 'op_instance': '2'}, {'op': 'splitvars', 'op_instance': '2'}, {'op': 'untar', 'op_instance': '2'}]
analyses                  {}                  
annotations               {'EPMT_JOB_TAGS': 'exp_component:ocean_cobalt_omip_tracers_year_z_1x1deg;exp_name:ESM4_hist-piNTCF_D151;exp_time:18890101;exp_platform:gfdl.ncrc4-intel16;exp_target:prod-openmp;exp_seg_months:12;script_name:ESM4_hist-piNTCF_D151_ocean_cobalt_omip_tracers_year_z_1x1deg_18890101'}
cancelled_write_bytes      458752              
cmajflt                   67                  
cminflt                   16211367            
cpu_time                  349260387.0         
created_at                2020-05-06 14:05:54.398645
cstime                    185450000           
cutime                    831780000           
delayacct_blkio_time      0                   
duration                  452759828.0         
end                       2020-05-06 14:00:17.835324
env_changes_dict          {'PWD': '/vftmp/Jeffrey.Durachta', 'OLDPWD': '/home/Jeffrey.Durachta', 'SLURM_GTIDS': '0', 'MPLCONFIGDIR': '/vftmp/Jeffrey.Durachta/job4899590/tmp4pdsbspm', 'SLURM_NODEID': '0', 'SLURM_JOB_GID': '70', 'SLURM_JOB_UID': '4067', 'SLURM_JOB_USER': 'Jeffrey.Durachta', 'SLURM_TASK_PID': '21523', 'SLURMD_NODENAME': 'pp055', 'SLURM_CPUS_ON_NODE': '1', 'SLURM_SCRIPT_CONTEXT': 'epilog_task'}
env_dict                  {'PWD': '/home/Jeffrey.Durachta', 'HOME': '/home/Jeffrey.Durachta', 'HOST': 'pp055', 'LANG': 'en_US', 'PATH': '/home/fms/local/opt/../epmt/3.7.22-centos-6/epmt-install/epmt:/home/gfdl/an+pp/bin:/app/slurm/default/bin:/bin:/usr/bin', 'TERM': 'linux', 'USER': 'Jeffrey.Durachta', 'GROUP': 'f', 'SHELL': '/bin/tcsh', 'SHLVL': '2', 'OSTYPE': 'linux', 'TMPDIR': '/vftmp/Jeffrey.Durachta/job4899590', 'VENDOR': 'unknown', 'ARCHIVE': '/archive/Jeffrey.Durachta', 'LC_TIME': 'C', 'LOGNAME': 'Jeffrey.Durachta', 'MANPATH': '/home/gfdl/man:/usr/local/man:/usr/share/man', 'HOSTNAME': 'pp055', 'HOSTTYPE': 'x86_64-linux', 'MACHTYPE': 'x86_64', 'MODULEPATH': '/usr/local/Modules/modulefiles:/home/fms/local/modulefiles', 'ENVIRONMENT': 'BATCH', 'MODULESHOME': '/usr/local/Modules/3.2.10', 'SLURM_GTIDS': '0', 'SLURM_JOBID': '4899590', 'MPLCONFIGDIR': '/vftmp/Jeffrey.Durachta/job4899590/tmpn961t07o', 'SLURM_JOB_ID': '4899590', 'SLURM_NNODES': '1', 'SLURM_NODEID': '0', 'SLURM_NPROCS': '1', 'SLURM_NTASKS': '1', 'SLURM_PROCID': '0', 'LOADEDMODULES': 'epmt/release', 'SBATCH_EXPORT': 'NONE', 'SLURM_JOB_GID': '70', 'SLURM_JOB_QOS': 'Added as default', 'SLURM_JOB_UID': '4067', 'SLURM_LOCALID': '0', 'MATPLOTLIBDATA': '/home/fms/local/epmt/3.7.22-centos-6/epmt-install/epmt/mpl-data', 'MODULE_VERSION': '3.2.10', 'SLURM_JOB_NAME': 'ESM4_hist-piNTCF_D151_ocean_cobalt_omip_tracers_year_z_1x1deg_18890101', 'SLURM_JOB_USER': 'Jeffrey.Durachta', 'SLURM_NODELIST': 'pp055', 'SLURM_TASK_PID': '21523', 'LD_LIBRARY_PATH': '/home/fms/local/epmt/3.7.22-centos-6/epmt-install/epmt', 'OMP_NUM_THREADS': '1', 'SLURMD_NODENAME': 'pp055', 'SLURM_RLIMIT_AS': '18446744073709551615', 'SLURM_EXPORT_ENV': 'NONE', 'SLURM_RLIMIT_CPU': '18446744073709551615', 'SLURM_RLIMIT_RSS': '18446744073709551615', 'SLURM_SUBMIT_DIR': '/home/Jeffrey.Durachta/CMIP6/ESM4/AerChemMIP/ESM4_hist-piNTCF_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess', 'SLURM_JOB_ACCOUNT': 'gfdl_f', 'SLURM_RLIMIT_CORE': '0', 'SLURM_RLIMIT_DATA': '18446744073709551615', 'SLURM_SUBMIT_HOST': 'an011', 'BASH_FUNC_module()': '() {  eval `/usr/local/Modules/$MODULE_VERSION/bin/modulecmd bash $*`\n}', 'SLURM_CLUSTER_NAME': 'gfdl', 'SLURM_CPUS_ON_NODE': '1', 'SLURM_GET_USER_ENV': '1', 'SLURM_JOB_NODELIST': 'pp055', 'SLURM_NODE_ALIASES': '(null)', 'SLURM_PRIO_PROCESS': '0', 'SLURM_RLIMIT_FSIZE': '18446744073709551615', 'SLURM_RLIMIT_NPROC': '8192', 'SLURM_RLIMIT_STACK': '18446744073709551615', 'SLURM_JOB_NUM_NODES': '1', 'SLURM_JOB_PARTITION': 'batch', 'SLURM_RLIMIT_NOFILE': '1024', 'SLURM_TOPOLOGY_ADDR': 'pp055', 'MODULE_VERSION_STACK': '3.2.10', 'SLURM_RLIMIT_MEMLOCK': '65536', 'SLURM_SCRIPT_CONTEXT': 'prolog_task', 'SLURM_TASKS_PER_NODE': '1', 'SLURM_WORKING_CLUSTER': 'gfdl:slurm01:6817:8704:101', 'SLURM_JOB_CPUS_PER_NODE': '1', 'SLURM_TOPOLOGY_ADDR_PATTERN': 'node'}
exitcode                  0                   
guest_time                0                   
inblock                   4085360             
info_dict                 {'tz': 'EDT', 'status': {'exit_code': 0, 'exit_reason': 'none', 'script_name': 'ESM4_hist-piNTCF_D151_ocean_cobalt_omip_tracers_year_z_1x1deg_18890101'}, 'post_processed': 1}
invol_ctxsw               10786               
jobid                     4899590             
jobname                   ESM4_hist-piNTCF_D151_ocean_cobalt_omip_tracers_year_z_1x1deg_18890101
majflt                    34                  
minflt                    6747682             
num_procs                 3396                
num_threads               3746                
outblock                  54483336            
processor                 0                   
rchar                     42314487327         
rdtsc_duration            8817115297050       
read_bytes                2091704320          
rssmax                    48866104            
start                     2020-05-06 13:52:45.075496
submit                    2020-05-06 13:52:45.075496
syscr                     6627074             
syscw                     1793104             
systemtime                72377336            
tags                      {'exp_name': 'ESM4_hist-piNTCF_D151', 'exp_time': '18890101', 'exp_target': 'prod-openmp', 'script_name': 'ESM4_hist-piNTCF_D151_ocean_cobalt_omip_tracers_year_z_1x1deg_18890101', 'exp_platform': 'gfdl.ncrc4-intel16', 'exp_component': 'ocean_cobalt_omip_tracers_year_z_1x1deg', 'exp_seg_months': '12'}
time_oncpu                351234143216        
time_waiting              18427277678         
timeslices                135878              
updated_at                2020-05-06 14:06:19.637884
user                      Jeffrey.Durachta    
usertime                  276883051           
vol_ctxsw                 121339              
wchar                     29175525734         
write_bytes               27895468032
```

### Dump job metadata file
```
$ ./epmt dump sample/kernel/run_output/job_metadata 
{'job_pl_id': 'kernel-build-20190606-150222', 'job_pl_submit_ts': datetime.datetime(2019, 6, 6, 15, 2, 22, 541326), 'job_pl_start_ts': datetime.datetime(2019, 6, 6, 15, 2, 22, 541326), 'job_el_reason': 'none', 'job_el_exitcode': 0, 'job_el_stop_ts': datetime.datetime(2019, 6, 6, 20, 39, 17, 792259), 'job_el_env': {'GOPATH': '/home/tushar/devhome/go', 'LS_COLORS': 'rs=0:di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=00:su=37;41:sg=30;43:ca=30;41:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arc=01;31:*.arj=01;31:*.taz=01;31:*.lha=01;31:*.lz4=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.Z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.jpg=01;35:*.jpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.ogv=01;35:*.ogx=01;35:*.aac=00;36:*.au=00;36:*.flac=00;36:*.m4a=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.oga=00;36:*.opus=00;36:*.spx=00;36:*.xspf=00;36:', 'rvm_version': '1.29.7 (latest)', 'GOBIN': '/home/tushar/devhome/platform/Linux-x86_64/bin', 'rvm_path': '/home/tushar/.rvm', 'LESSOPEN': '| /usr/bin/lesspipe %s', 'SSH_CLIENT': '192.168.254.108 32832 22', 'LOGNAME': 'tushar', 'USER': 'tushar', 'HOME': '/home/tushar', 'PATH': '/home/tushar/.rvm/bin:/usr/local/bin:.:./bin:/home/tushar/bin:/home/tushar/devhome/platform/Linux-x86_64/bin:/home/tushar/.rvm/bin:/usr/local/bin:.:./bin:/home/tushar/bin:/home/tushar/devhome/platform/Linux-x86_64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/home/tushar/.rvm/bin:/home/tushar/.rvm/bin:/home/tushar/devhome/bin:/home/tushar/.local/bin:/home/tushar/.rvm/bin:/home/tushar/.rvm/bin:/home/tushar/devhome/bin:/home/tushar/.local/bin', 'HISTSIZE': '10000000', 'LANG': 'en_IN', 'TERM': 'screen', 'SHELL': '/bin/bash', 'K8_KVM_SECONDARY_DISK': '25G', 'K8_KVM_NODE_MEMORY': '2048', 'LANGUAGE': 'en_IN:en', 'SHLVL': '2', 'K8_KVM_NUM_SLAVES': '2', 'QT_QPA_PLATFORMTHEME': 'appmenu-qt5', 'KUBECONFIG': '/home/tushar/src/k8s-kvm/kube.config', 'K8_KVM_MASTER_MEMORY': '2048', 'LIBVIRT_DEFAULT_URI': 'qemu:///system', 'rvm_bin_path': '/home/tushar/.rvm/bin', 'XDG_RUNTIME_DIR': '/run/user/1000', 'rvm_prefix': '/home/tushar', 'TMUX': '/tmp/tmux-1000/default,3744,0', 'EDITOR': 'vim', 'XDG_DATA_DIRS': '/usr/local/share:/usr/share:/var/lib/snapd/desktop', 'XDG_SESSION_ID': '107075', 'TMPDIR': '/scratch', 'SUBNET': '192.168.40', 'LSCOLORS': 'GxFxCxDxBxegedabagaced', 'LESSCLOSE': '/usr/bin/lesspipe %s %s', 'EPMT_JOB_TAGS': 'model:linux-kernel;compiler:gcc', 'PYTHONSTARTUP': '/home/tushar/devhome/rc/pystartup', 'SSH_TTY': '/dev/pts/0', 'OLDPWD': '/home/tushar', 'CLICOLOR': '1', 'NUM_SLAVES': '2', 'PWD': '/home/tushar/mm/epmt/build/epmt', 'MAIL': '/var/mail/tushar', 'SSH_CONNECTION': '192.168.254.108 42414 192.168.254.121 22', 'TMUX_PANE': '%13'}, 'job_pl_env': {'GOPATH': '/home/tushar/devhome/go', 'rvm_version': '1.29.7 (latest)', 'GOBIN': '/home/tushar/devhome/platform/Linux-x86_64/bin', 'rvm_path': '/home/tushar/.rvm', 'LESSOPEN': '| /usr/bin/lesspipe %s', 'SSH_CLIENT': '192.168.254.108 32832 22', 'LOGNAME': 'tushar', 'USER': 'tushar', 'HOME': '/home/tushar', 'PATH': '/home/tushar/.rvm/bin:/usr/local/bin:.:./bin:/home/tushar/bin:/home/tushar/devhome/platform/Linux-x86_64/bin:/home/tushar/.rvm/bin:/usr/local/bin:.:./bin:/home/tushar/bin:/home/tushar/devhome/platform/Linux-x86_64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/home/tushar/.rvm/bin:/home/tushar/.rvm/bin:/home/tushar/devhome/bin:/home/tushar/.local/bin:/home/tushar/.rvm/bin:/home/tushar/.rvm/bin:/home/tushar/devhome/bin:/home/tushar/.local/bin', 'KUBECONFIG': '/home/tushar/src/k8s-kvm/kube.config', 'SSH_CONNECTION': '192.168.254.108 42414 192.168.254.121 22', 'LANG': 'en_IN', 'TERM': 'screen', 'SHELL': '/bin/bash', 'K8_KVM_SECONDARY_DISK': '25G', 'K8_KVM_NODE_MEMORY': '2048', 'LANGUAGE': 'en_IN:en', 'NUM_SLAVES': '2', 'SHLVL': '2', 'K8_KVM_NUM_SLAVES': '2', 'QT_QPA_PLATFORMTHEME': 'appmenu-qt5', 'HISTSIZE': '10000000', 'K8_KVM_MASTER_MEMORY': '2048', 'LIBVIRT_DEFAULT_URI': 'qemu:///system', 'rvm_bin_path': '/home/tushar/.rvm/bin', 'XDG_RUNTIME_DIR': '/run/user/1000', 'rvm_prefix': '/home/tushar', 'TMUX': '/tmp/tmux-1000/default,3744,0', 'EDITOR': 'vim', 'XDG_SESSION_ID': '107075', 'TMPDIR': '/scratch', 'SUBNET': '192.168.40', 'LSCOLORS': 'GxFxCxDxBxegedabagaced', 'LESSCLOSE': '/usr/bin/lesspipe %s %s', 'EPMT_JOB_TAGS': 'model:linux-kernel;compiler:gcc', 'PYTHONSTARTUP': '/home/tushar/devhome/rc/pystartup', 'SSH_TTY': '/dev/pts/0', 'OLDPWD': '/home/tushar', 'CLICOLOR': '1', 'XDG_DATA_DIRS': '/usr/local/share:/usr/share:/var/lib/snapd/desktop', 'PWD': '/home/tushar/mm/epmt/build/epmt', 'MAIL': '/var/mail/tushar', 'LS_COLORS': 'rs=0:di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=00:su=37;41:sg=30;43:ca=30;41:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arc=01;31:*.arj=01;31:*.taz=01;31:*.lha=01;31:*.lz4=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.Z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.jpg=01;35:*.jpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.ogv=01;35:*.ogx=01;35:*.aac=00;36:*.au=00;36:*.flac=00;36:*.m4a=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.oga=00;36:*.opus=00;36:*.spx=00;36:*.xspf=00;36:', 'TMUX_PANE': '%13'}}
job_el_env              {'GOPATH': '/home/tushar/devhome/go', 'LS_COLORS': 'rs=0:di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=00:su=37;41:sg=30;43:ca=30;41:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arc=01;31:*.arj=01;31:*.taz=01;31:*.lha=01;31:*.lz4=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.Z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.jpg=01;35:*.jpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.ogv=01;35:*.ogx=01;35:*.aac=00;36:*.au=00;36:*.flac=00;36:*.m4a=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.oga=00;36:*.opus=00;36:*.spx=00;36:*.xspf=00;36:', 'rvm_version': '1.29.7 (latest)', 'GOBIN': '/home/tushar/devhome/platform/Linux-x86_64/bin', 'rvm_path': '/home/tushar/.rvm', 'LESSOPEN': '| /usr/bin/lesspipe %s', 'SSH_CLIENT': '192.168.254.108 32832 22', 'LOGNAME': 'tushar', 'USER': 'tushar', 'HOME': '/home/tushar', 'PATH': '/home/tushar/.rvm/bin:/usr/local/bin:.:./bin:/home/tushar/bin:/home/tushar/devhome/platform/Linux-x86_64/bin:/home/tushar/.rvm/bin:/usr/local/bin:.:./bin:/home/tushar/bin:/home/tushar/devhome/platform/Linux-x86_64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/home/tushar/.rvm/bin:/home/tushar/.rvm/bin:/home/tushar/devhome/bin:/home/tushar/.local/bin:/home/tushar/.rvm/bin:/home/tushar/.rvm/bin:/home/tushar/devhome/bin:/home/tushar/.local/bin', 'HISTSIZE': '10000000', 'LANG': 'en_IN', 'TERM': 'screen', 'SHELL': '/bin/bash', 'K8_KVM_SECONDARY_DISK': '25G', 'K8_KVM_NODE_MEMORY': '2048', 'LANGUAGE': 'en_IN:en', 'SHLVL': '2', 'K8_KVM_NUM_SLAVES': '2', 'QT_QPA_PLATFORMTHEME': 'appmenu-qt5', 'KUBECONFIG': '/home/tushar/src/k8s-kvm/kube.config', 'K8_KVM_MASTER_MEMORY': '2048', 'LIBVIRT_DEFAULT_URI': 'qemu:///system', 'rvm_bin_path': '/home/tushar/.rvm/bin', 'XDG_RUNTIME_DIR': '/run/user/1000', 'rvm_prefix': '/home/tushar', 'TMUX': '/tmp/tmux-1000/default,3744,0', 'EDITOR': 'vim', 'XDG_DATA_DIRS': '/usr/local/share:/usr/share:/var/lib/snapd/desktop', 'XDG_SESSION_ID': '107075', 'TMPDIR': '/scratch', 'SUBNET': '192.168.40', 'LSCOLORS': 'GxFxCxDxBxegedabagaced', 'LESSCLOSE': '/usr/bin/lesspipe %s %s', 'EPMT_JOB_TAGS': 'model:linux-kernel;compiler:gcc', 'PYTHONSTARTUP': '/home/tushar/devhome/rc/pystartup', 'SSH_TTY': '/dev/pts/0', 'OLDPWD': '/home/tushar', 'CLICOLOR': '1', 'NUM_SLAVES': '2', 'PWD': '/home/tushar/mm/epmt/build/epmt', 'MAIL': '/var/mail/tushar', 'SSH_CONNECTION': '192.168.254.108 42414 192.168.254.121 22', 'TMUX_PANE': '%13'}
job_el_exitcode         0                                                       
job_el_reason           none                                                    
job_el_stop_ts          2019-06-06 20:39:17.792259                              
job_pl_env              {'GOPATH': '/home/tushar/devhome/go', 'rvm_version': '1.29.7 (latest)', 'GOBIN': '/home/tushar/devhome/platform/Linux-x86_64/bin', 'rvm_path': '/home/tushar/.rvm', 'LESSOPEN': '| /usr/bin/lesspipe %s', 'SSH_CLIENT': '192.168.254.108 32832 22', 'LOGNAME': 'tushar', 'USER': 'tushar', 'HOME': '/home/tushar', 'PATH': '/home/tushar/.rvm/bin:/usr/local/bin:.:./bin:/home/tushar/bin:/home/tushar/devhome/platform/Linux-x86_64/bin:/home/tushar/.rvm/bin:/usr/local/bin:.:./bin:/home/tushar/bin:/home/tushar/devhome/platform/Linux-x86_64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/home/tushar/.rvm/bin:/home/tushar/.rvm/bin:/home/tushar/devhome/bin:/home/tushar/.local/bin:/home/tushar/.rvm/bin:/home/tushar/.rvm/bin:/home/tushar/devhome/bin:/home/tushar/.local/bin', 'KUBECONFIG': '/home/tushar/src/k8s-kvm/kube.config', 'SSH_CONNECTION': '192.168.254.108 42414 192.168.254.121 22', 'LANG': 'en_IN', 'TERM': 'screen', 'SHELL': '/bin/bash', 'K8_KVM_SECONDARY_DISK': '25G', 'K8_KVM_NODE_MEMORY': '2048', 'LANGUAGE': 'en_IN:en', 'NUM_SLAVES': '2', 'SHLVL': '2', 'K8_KVM_NUM_SLAVES': '2', 'QT_QPA_PLATFORMTHEME': 'appmenu-qt5', 'HISTSIZE': '10000000', 'K8_KVM_MASTER_MEMORY': '2048', 'LIBVIRT_DEFAULT_URI': 'qemu:///system', 'rvm_bin_path': '/home/tushar/.rvm/bin', 'XDG_RUNTIME_DIR': '/run/user/1000', 'rvm_prefix': '/home/tushar', 'TMUX': '/tmp/tmux-1000/default,3744,0', 'EDITOR': 'vim', 'XDG_SESSION_ID': '107075', 'TMPDIR': '/scratch', 'SUBNET': '192.168.40', 'LSCOLORS': 'GxFxCxDxBxegedabagaced', 'LESSCLOSE': '/usr/bin/lesspipe %s %s', 'EPMT_JOB_TAGS': 'model:linux-kernel;compiler:gcc', 'PYTHONSTARTUP': '/home/tushar/devhome/rc/pystartup', 'SSH_TTY': '/dev/pts/0', 'OLDPWD': '/home/tushar', 'CLICOLOR': '1', 'XDG_DATA_DIRS': '/usr/local/share:/usr/share:/var/lib/snapd/desktop', 'PWD': '/home/tushar/mm/epmt/build/epmt', 'MAIL': '/var/mail/tushar', 'LS_COLORS': 'rs=0:di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=00:su=37;41:sg=30;43:ca=30;41:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arc=01;31:*.arj=01;31:*.taz=01;31:*.lha=01;31:*.lz4=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.Z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.jpg=01;35:*.jpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.ogv=01;35:*.ogx=01;35:*.aac=00;36:*.au=00;36:*.flac=00;36:*.m4a=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.oga=00;36:*.opus=00;36:*.spx=00;36:*.xspf=00;36:', 'TMUX_PANE': '%13'}
job_pl_id               kernel-build-20190606-150222                            
job_pl_start_ts         2019-06-06 15:02:22.541326                              
job_pl_submit_ts        2019-06-06 15:02:22.541326 
```

You can pass the ***-k*** key switch and a requested key parameter also.

```text
./epmt dump -k job_tags sample/ppr-batch-sow3/1909/2587750.tgz 
{'exp_name': 'ESM4_hist-piAer_D1', 'exp_component': 'ocean_cobalt_sfc', 'exp_time': '19090101', 'atm_res': 'c96l49', 'ocn_res': '0.5l75', 'script_name': 'ESM4_hist-piAer_D1_ocean_cobalt_sfc_19090101'}
```
