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
check: check-python-shells check-unittests

#SLURM_FAKE_JOB_ID=1
#FORCE_DEFAULT_SETTINGS=EPMT_USE_DEFAULT_SETTINGS=1 SLURM_JOB_ID=1 SLURM_JOB_USER=`whoami` 
#TMP_OUTPUT_DIR=/tmp/epmt/
#DOCKER_PYTHON_IMAGE=
#DOCKER_RUN_PYTHON=docker run -ti --rm -v $(shell pwd):/app -w /app -e PAPIEX_OUTPUT=$(TMP_OUTPUT_DIR) -e SLURM_JOB_ID=$(SLURM_FAKE_JOB_ID) -e EPMT_JOB_TAGS=operation:test -e $(FORCE_DEFAULT_SETTINGS)

#check-python-2.6: 
#	@$(MAKE) DOCKER_PYTHON_IMAGE=lovato/python-2.6.6 check-python-driver
#check-python-2.7: 
#	@$(MAKE) DOCKER_PYTHON_IMAGE=python:2.7 check-python-driver
#check-python-3: 
#	@$(MAKE) DOCKER_PYTHON_IMAGE=python:3 check-python-driver
#check-python-native:
#	@$(MAKE) DOCKER_RUN_PYTHON="PAPIEX_OUTPUT=$(TMP_OUTPUT_DIR) SLURM_JOB_ID=$(SLURM_FAKE_JOB_ID) EPMT_JOB_TAGS=operation:test"  DOCKER_PYTHON_IMAGE="" check-python-driver

EPMT_TEST_ENV=PATH=${PWD}:${PATH} SLURM_JOB_ID=1 SLURM_JOB_USER=`whoami` EPMT_USE_DEFAULT_SETTINGS=1

check-python-shells:
	@if [ -d /tmp/epmt ]; then echo "Directory /tmp/epmt exists! Hit return to remove it, Control-C to stop now."; read yesno; fi
	rm -rf /tmp/epmt
	env -i ${EPMT_TEST_ENV} /bin/tcsh -e epmt-example.csh
	rm -rf /tmp/epmt
	env -i ${EPMT_TEST_ENV} /bin/bash -Eeu epmt-example.sh
	rm -rf /tmp/epmt
check-unittests:
	@echo; echo "Testing built in unit tests..."
	env -i PATH=${PWD}:${PATH} EPMT_USE_DEFAULT_SETTINGS=1 python3 -m unittest -v -f test.test_misc test.test_query test.test_db_schema test.test_submit test.test_outliers 
