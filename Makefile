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

EPMT_TEST_ENV=PATH=${PWD}:${PATH} SLURM_JOB_USER=`whoami`

check-python-shells:
	@if [ -d /tmp/epmt ]; then echo "Directory /tmp/epmt exists! Hit return to remove it, Control-C to stop now."; read yesno; fi
	@rm -rf /tmp/epmt
	@echo "epmt-example.csh (tcsh)" ; env -i SLURM_JOB_ID=1 ${EPMT_TEST_ENV} /bin/tcsh -e epmt-example.csh
	@rm -rf /tmp/epmt
	@echo "epmt-example.sh (bash)" ; env -i SLURM_JOB_ID=2 ${EPMT_TEST_ENV} /bin/bash -Eeu epmt-example.sh
	@rm -rf /tmp/epmt
check-unittests:
	@echo; echo "Testing built-in unit tests..."
	@env -i PATH=${PWD}:${PATH} python3 -m unittest -v -f test.test_submit test.test_misc test.test_query test.test_outliers test.test_db_schema
