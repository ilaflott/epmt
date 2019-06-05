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
