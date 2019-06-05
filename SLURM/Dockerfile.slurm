# This must be run from one directory above
# ./papiex-oss.git
# ./epmt.git
FROM giovtorres/docker-centos7-slurm:latest as slurm
COPY epmt.git/requirements.txt /tmp
# EPMT Requirements
WORKDIR /tmp
RUN pip install -r requirements.txt
RUN rm -f requirements.txt
# EPMT Install
WORKDIR /opt/epmt
COPY epmt.git/models /opt/epmt/models
COPY epmt.git/epmt epmt.git/epmt_job.py epmt.git/epmt_cmds.py /opt/epmt/
COPY epmt.git/settings/settings_slurm_test.py /opt/epmt/settings.py
RUN python -m py_compile epmt *.py models/*.py
# SLURM integration
COPY epmt.git/SLURM/slurm_task_prolog_epmt.sh epmt.git/SLURM/slurm_task_epilog_epmt.sh /opt/epmt/
RUN echo "TaskProlog=/opt/epmt/slurm_task_prolog_epmt.sh" >> /etc/slurm/slurm.conf
RUN echo "TaskEpilog=/opt/epmt/slurm_task_epilog_epmt.sh" >> /etc/slurm/slurm.conf
# PAPIEX Install
COPY ./papiex-oss.git /tmp/papiex-oss.git
WORKDIR /tmp/papiex-oss.git
RUN make PREFIX=/opt/papiex install
RUN rm -rf /tmp/papiex-oss.git
