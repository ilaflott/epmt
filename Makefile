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
check: check-python-driver-bash check-python-driver-sh check-python-driver-tcsh check-python-driver-csh check-example-csh check-example-bash check-stage-submit check-unittests

SLURM_FAKE_JOB_ID=1
FORCE_DEFAULT_SETTINGS=EPMT_USE_DEFAULT_SETTINGS=1
TMP_OUTPUT_DIR=/tmp/epmt/
DOCKER_PYTHON_IMAGE=
DOCKER_RUN_PYTHON=docker run -ti --rm -v $(shell pwd):/app -w /app -e PAPIEX_OUTPUT=$(TMP_OUTPUT_DIR) -e SLURM_JOB_ID=$(SLURM_FAKE_JOB_ID) -e EPMT_JOB_TAGS=operation:test -e $(FORCE_DEFAULT_SETTINGS)

check-python-2.6: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=lovato/python-2.6.6 check-python-driver
check-python-2.7: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=python:2.7 check-python-driver
check-python-3: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=python:3 check-python-driver
check-python-native:
	@$(MAKE) DOCKER_RUN_PYTHON="PAPIEX_OUTPUT=$(TMP_OUTPUT_DIR) SLURM_JOB_ID=$(SLURM_FAKE_JOB_ID) EPMT_JOB_TAGS=operation:test"  DOCKER_PYTHON_IMAGE="" check-python-driver

check-python-driver-bash:
	@echo; echo "Testing /bin/bash..."
	env -i PATH=$(PWD):$$PATH $(FORCE_DEFAULT_SETTINGS) /bin/bash -x epmt-check.anysh
check-python-driver-sh:
	@echo; echo "Testing /bin/sh..."
	env -i PATH=$(PWD):$$PATH $(FORCE_DEFAULT_SETTINGS) /bin/sh -x epmt-check.anysh
check-python-driver-tcsh:
	@echo; echo "Testing /bin/tcsh..."
	env -i PATH=$(PWD):$$PATH $(FORCE_DEFAULT_SETTINGS) /bin/csh -v epmt-check.anysh
check-python-driver-csh:
	@echo; echo "Testing /bin/csh..."
	env -i PATH=$(PWD):$$PATH $(FORCE_DEFAULT_SETTINGS) /bin/csh -v epmt-check.anysh
check-example-bash:
	@echo; echo "Testing /bin/csh with epmt-example.csh..."
	env -i PATH=$(PWD):$(PATH) $(FORCE_DEFAULT_SETTINGS) /bin/bash -Eeux epmt-example.anysh
check-example-csh:
	@echo; echo "Testing /bin/csh with epmt-example.csh..."
	env -i PATH=$(PWD):$(PATH) $(FORCE_DEFAULT_SETTINGS) /bin/csh -ve epmt-example.csh
check-stage-submit:
	@echo; echo "Testing sample data stage/submit with epmt-check-stage-submit.sh..."
	env -i PATH=$(PWD):$(PATH) $(FORCE_DEFAULT_SETTINGS) /bin/bash epmt-check-stage-submit.sh
check-unittests:
	@echo; echo "Testing built in unit tests..."
	env -i PATH=$(PWD):$(PATH) $(FORCE_DEFAULT_SETTINGS) python -m unittest discover -s test -v

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
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt submit ./$(SLURM_FAKE_JOB_ID).tgz # Submit from staged storage
	@$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) python -V	            # Version 
	@echo "Tests pass!"
