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

check-python-native:
	@if [ -f ./job_metadata ]; then echo "Please remove ./job_metadata first."; exit 1; fi
	python -m py_compile *.py models/*.py			# Compile everything
	PAPIEX_OUTPUT=$(PWD)/ python ./epmt_cmds.py -h 		# Help
	PAPIEX_OUTPUT=$(PWD)/ python ./epmt_cmds.py start 	# Generate prolog
	sleep 1
	PAPIEX_OUTPUT=$(PWD)/ python ./epmt_cmds.py stop 	# Generate epilog and append
	PAPIEX_OUTPUT=$(PWD)/ python ./epmt_cmds.py dump 	# Verify
	PAPIEX_OUTPUT=$(PWD)/ python ./epmt_cmds.py -n run /bin/sleep 1 # run dry
	PAPIEX_OUTPUT=$(PWD)/ python ./epmt_cmds.py -n -a run /bin/sleep 1	# run dry + auto
	@python -V
	@echo "Tests pass!"
#	python ./epmt_cmds.py -d submit $(PWD)/	       	    	# Parse metadata

check-python-2.6:
# syntax check of all
	@if [ -f ./job_metadata ]; then echo "Please remove ./job_metadata first."; exit 1; fi
	docker run -ti --rm -v `pwd`:/app -w /app lovato/python-2.6.6 python -m py_compile *.py models/*.py
# just usage
	docker run -ti --rm -v `pwd`:/app -w /app lovato/python-2.6.6 python ./epmt_cmds.py -h
# start
	docker run -ti --rm -v `pwd`:/app -w /app -e PAPIEX_OUTPUT=/app/ lovato/python-2.6.6 python ./epmt_cmds.py start
# stop
	docker run -ti --rm -v `pwd`:/app -w /app -e PAPIEX_OUTPUT=/app/ lovato/python-2.6.6 python ./epmt_cmds.py stop
# dump
	docker run -ti --rm -v `pwd`:/app -w /app -e PAPIEX_OUTPUT=/app/ lovato/python-2.6.6 python ./epmt_cmds.py dump
# run dry
	docker run -ti --rm -v `pwd`:/app -w /app -e PAPIEX_OUTPUT=/app/ lovato/python-2.6.6 python ./epmt_cmds.py -n run /bin/sleep 1
# run dry + auto
	docker run -ti --rm -v `pwd`:/app -w /app -e PAPIEX_OUTPUT=/app/ lovato/python-2.6.6 python ./epmt_cmds.py -n -a run /bin/sleep 1
# version
	@docker run -ti --rm -v `pwd`:/app -w /app lovato/python-2.6.6 python -V
	@echo "Tests pass!"
