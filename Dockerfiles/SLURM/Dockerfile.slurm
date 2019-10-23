FROM phusion/baseimage:0.10.2

RUN install_clean slurm-wlm
COPY slurm.conf /etc/slurm-llnl
COPY slurmdbd.conf /etc/slurm-llnl
RUN mkdir /var/spool/slurm-llnl
RUN update-rc.d slurmd enable && update-rc.d slurmctld enable && update-rc.d munge enable
COPY startup-slurm.sh /etc/my_init.d

# ENTRYPOINT ["python"]
# When run without anything, print help
CMD ["/sbin/my_init","--","/bin/bash" ]
