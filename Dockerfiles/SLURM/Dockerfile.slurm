FROM phusion/baseimage:0.10.2

RUN install_clean slurm-wlm
COPY slurm.conf /etc/slurm-llnl
COPY slurmdbd.conf /etc/slurm-llnl
RUN mkdir /var/spool/slurm-llnl && mkdir -p /var/run/slurm-llnl/slurmd && mkdir -p /var/lib/slurm-llnl/slurmd

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD ["slurmctld"]
