PYTHON?=python
SHELL=/bin/bash

.PHONY: epmt-build epmt-test default clean distclean check
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
check: 
	python -m py_compile *.py models/*.py			# Compile everything
	PAPIEX_OUTPUT=$(PWD)/ python ./epmt_cmds.py -d start 	# Generate prolog
	sleep 1	      	     		       			# wait
	PAPIEX_OUTPUT=$(PWD)/ python ./epmt_cmds.py -d stop 	# Generate epilog and append
	python ./epmt_job.py -d -n $(PWD)/	       	    	# Parse metadata
#	python ./epmt_cmds.py -d submit $(PWD)/	       	    	# Parse metadata
