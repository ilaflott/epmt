## BUGS

* We only handle ONE job step in SLURM allocations, that is the submitted script.
 * srun in an empty script is essentially the second job step - currently not handled.
* Stage/collation does not work on 'remote' nodes, ie any sruns.

# Environment build

  See output of:
      make -n docker-dist-slurm 
      make -n docker-test-dist-slurm
      
  make slurm-start

  Starts SLURM image in background named slurm

  make slurm-stop

  Stops the above SLURM image

  docker exec centos7-slurm epmt submit ./sample/615503.tgz

  Runs the command on the above SLURM image
  
## SLURM Notes

TaskProlog and TaskEpilog are not run:
 * salloc

But are run during:
 * sbatch
 * srun

## Docker Notes

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

