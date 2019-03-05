SHELL=/bin/bash

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
	rm -f *~ *.pyc job_metadata *papiex*.csv
distclean: clean
	rm -f settings.py; ln -s settings/settings_sqlite_inmem.py settings.py  # Setup in mem sqlite
# 
# Simple python version testing with no database
#
check: check-python-native

DOCKER_PYTHON_IMAGE=
DOCKER_RUN_PYTHON=docker run -ti --rm -v $(shell pwd):/app -w /app -e PAPIEX_OUTPUT=/app/

check-python-2.6: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=lovato/python-2.6.6 check-python-driver
check-python-2.7: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=python:2.7 check-python-driver
check-python-3: 
	@$(MAKE) DOCKER_PYTHON_IMAGE=python:3 check-python-driver
check-python-native:
	@$(MAKE) DOCKER_RUN_PYTHON="PAPIEX_OUTPUT=$$PWD" DOCKER_PYTHON_IMAGE="" check-python-driver

check-python-driver:
	@if [ -f ./job_metadata ]; then echo "Please remove ./job_metadata first."; exit 1; fi
	@rm -f settings.py; ln -s settings/settings_sqlite_inmem.py settings.py  # Setup in mem sqlite
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) python -m py_compile *.py models/*.py         # Compile everything
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt -h >/dev/null      # help path 1
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt help >/dev/null    # help path 2
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt start           # Generate prolog
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt source          # Print shell command
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt run sleep 1     # Run command
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt stop            # Generate epilog and append
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt dump            # Parse/print job_metadata
	$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) ./epmt -n submit       # Submit
	@$(DOCKER_RUN_PYTHON) $(DOCKER_PYTHON_IMAGE) python -V	             # Version 
	@echo "Tests pass!"
	@rm ./job_metadata
