PYTHON?=python
SHELL=/bin/bash

.PHONY: epmt-build epmt-test default clean distclean check check-python-native check-python-2.6
default: epmt-build epmt-test
epmt-build:
	docker build -f Dockerfiles/Dockerfile.python-epmt -t python-epmt:latest --squash .
	docker build -f Dockerfiles/Dockerfile.epmt-command -t epmt-command:latest --squash .
	docker build -f Dockerfiles/Dockerfile.epmt-papiex -t epmt-papiex:latest --squash .
	docker-compose build
epmt-test:
	docker run epmt:latest
#	docker-compose up
clean distclean:
	rm -f *~ *.pyc job_metadata *papiex*.csv
# Testing
check: check-python-native

#
# Native python should have all dependencies installed
#
check-python-native:
	@if [ -f ./job_metadata ]; then echo "Please remove ./job_metadata first."; exit 1; fi
	python -m py_compile *.py models/*.py         # Compile everything
	PAPIEX_OUTPUT=$(PWD)/ ./epmt -h >/dev/null      # help path 1
	PAPIEX_OUTPUT=$(PWD)/ ./epmt help >/dev/null    # help path 2
	PAPIEX_OUTPUT=$(PWD)/ ./epmt -d start           # Generate prolog
	PAPIEX_OUTPUT=$(PWD)/ ./epmt -d source          # Print shell command
	PAPIEX_OUTPUT=$(PWD)/ ./epmt -d run sleep 1     # Run command
	PAPIEX_OUTPUT=$(PWD)/ ./epmt -d stop            # Generate epilog and append
	PAPIEX_OUTPUT=$(PWD)/ ./epmt -d dump            # Parse/print job_metadata
	@rm -f settings.py; cp settings_sqllite.py settings.py  # Setup in mem sqlite
	PAPIEX_OUTPUT=$(PWD)/ ./epmt -d submit          # Submit
	@python -V
	@echo "Tests pass!"

#
# Assume this image has no dependencies installed so we just dry-run a submit
#
DOCKER_RUN_PY26=docker run -ti --rm -v $(shell pwd):/app -w /app -e PAPIEX_OUTPUT=/app/ lovato/python-2.6.6
check-python-2.6:
	@if [ -f ./job_metadata ]; then echo "Please remove ./job_metadata first."; exit 1; fi
	$(DOCKER_RUN_PY26) python -m py_compile *.py models/*.py         # Compile everything
	$(DOCKER_RUN_PY26) ./epmt -h >/dev/null      # help path 1
	$(DOCKER_RUN_PY26) ./epmt help >/dev/null    # help path 2
	$(DOCKER_RUN_PY26) ./epmt -d start           # Generate prolog
	$(DOCKER_RUN_PY26) ./epmt -d source          # Print shell command
	$(DOCKER_RUN_PY26) ./epmt -d run sleep 1     # Run command
	$(DOCKER_RUN_PY26) ./epmt -d stop            # Generate epilog and append
	$(DOCKER_RUN_PY26) ./epmt -d dump            # Parse/print job_metadata
	@rm -f settings.py; cp settings_sqllite.py settings.py  # Setup in mem sqlite
	$(DOCKER_RUN_PY26) ./epmt -n -d submit          # Submit
	@$(DOCKER_RUN_PY26) python -V			     # Version 
	@echo "Tests pass!"
