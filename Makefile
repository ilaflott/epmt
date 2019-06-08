SHELL=/bin/sh
#export SHELL

.PHONY: default \\
	epmt-build epmt-test \\
	clean distclean \\
	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3

default: epmt-build epmt-build-stack

epmt-build: Dockerfiles/Dockerfile.python-epmt Dockerfiles/Dockerfile.epmt-command Dockerfiles/Dockerfile.epmt-notebook
	docker build -f Dockerfiles/Dockerfile.python-epmt -t python-epmt:latest --squash .
	docker build -f Dockerfiles/Dockerfile.epmt-command -t epmt-command:latest --squash .
	docker build -f Dockerfiles/Dockerfile.epmt-notebook -t epmt-notebook:latest --squash .

epmt-build-stack: epmt-build docker-compose.yml
	docker-compose build
#epmt-test:
#	docker run epmt:latest
#	docker-compose up
clean:
	rm -f *~ *.pyc 
	rm -rf __pycache__
distclean: clean
	rm -f settings.py; ln -s settings/settings_sqlite_inmem.py settings.py  # Setup in mem sqlite
# 
# Simple python version testing with no database
#
check: check-python-native

SLURM_FAKE_JOB_ID=1
TMP_OUTPUT_DIR=/tmp/epmt/
DOCKER_PYTHON_IMAGE=
DOCKER_RUN_PYTHON=docker run -ti --rm -v $(shell pwd):/app -w /app -e PAPIEX_OUTPUT=$(TMP_OUTPUT_DIR) -e SLURM_JOB_ID=$(SLURM_FAKE_JOB_ID) -e EPMT_JOB_TAGS=operation:test

check-python-2.6: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=lovato/python-2.6.6 check-python-driver
check-python-2.7: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=python:2.7 check-python-driver
check-python-3: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=python:3 check-python-driver
check-python-native:
	@$(MAKE) DOCKER_RUN_PYTHON="PAPIEX_OUTPUT=$(TMP_OUTPUT_DIR) SLURM_JOB_ID=$(SLURM_FAKE_JOB_ID) EPMT_JOB_TAGS=operation:test"  DOCKER_PYTHON_IMAGE="" check-python-driver

check-python-driver-csh:
	env -i PATH=$(PWD):$$PATH /bin/csh epmt-check.anysh
check-python-driver-bash:
	PATH=$(PWD):$$PATH /bin/bash epmt-check.anysh
check-python-driver:
#	@rm -fr $(TMP_OUTPUT_DIR) $(SLURM_FAKE_JOB_ID);
	@rm -f settings.py; ln -s settings/settings_sqlite_inmem.py settings.py  # Setup in mem sqlite
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) python -m py_compile epmt *.py models/*.py         # Compile everything
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt -h >/dev/null      # help path 1
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt help >/dev/null    # help path 2
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt start           # Generate prolog
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt source          # Print shell command
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt run sleep 1     # Run command, if no papiex just run command silently
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt stop            # Generate epilog and append
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt dump >/dev/null # Parse/print job_metadata
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt stage           # Move to medium term storage
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt submit ./$(SLURM_FAKE_JOB_ID)/ # Submit from staged storage
	@$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) python -V	            # Version 
	@echo "Tests pass!"
