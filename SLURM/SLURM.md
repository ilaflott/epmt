## BUGS

* We only handle ONE job step in SLURM allocations, that is the submitted script.

# Environment build
cd ../..
docker build -f epmt.git/SLURM/Dockerfile.slurm -t slurm-epmt-papiex:latest .

# Environment run
scuba -r -d=-h -d=ernie -d=--privileged --image slurm-epmt-papiex

# Environment test
[root@ernie GFDL]# srun -n1 sleep 10
[root@ernie GFDL]# ls /tmp/epmt/3/
ernie-papiex-806-0.csv  job_metadata
[root@ernie GFDL]# srun -n1 hostname
ernie
[root@ernie GFDL]# ls /tmp/epmt/4
ernie-papiex-848-0.csv  job_metadata

SLURM 19 and a later kernel, plus all pythons
https://github.com/giovtorres/docker-centos7-slurm
docker pull giovtorres/docker-centos7-slurm:latest
docker run -it -h ernie giovtorres/docker-centos7-slurm:latest
docker-compose up -d

For SLURM 18
https://hub.docker.com/r/giovtorres/slurm-docker-cluster
docker pull giovtorres/slurm-docker-cluster
docker-compose up -d

For SLURM 17 and below
https://github.com/giovtorres/docker-centos6-slurm
docker pull giovtorres/docker-centos6-slurm:latest
docker run -it -h ernie giovtorres/docker-centos6-slurm:latest

## SLURM Notes

TaskProlog and TaskEpilog are not run:
 * salloc

But are run during:
 * sbatch
 * srun