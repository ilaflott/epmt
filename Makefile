SHELL=/bin/sh
#export SHELL

.PHONY: default build \\
	epmt-build epmt-test \\
	clean distclean \\
	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3

build:
	python -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py

dist default: 
	docker build -f Dockerfiles/Dockerfile.python-epmt -t python-epmt:latest .
	dir=`date "+epmt-build-%Y-%m-%d-%H:%M:%S"`; docker run -i --tty --rm --volume=$$PWD:$$PWD:z -w $$PWD --privileged epmt-python pyinstaller --clean --hidden-import epmt_default_settings --exclude-module settings --distpath=$$dir -s epmt

clean:
	find . -name "*~" -o -name "*.pyc" -exec rm -f {} \; 
	rm -rf __pycache__
distclean: clean
	rm -f settings.py; ln -s preset_settings/settings_sqlite_inmem_sqlalchemy.py settings.py # Setup in mem sqlite
# 
# Simple python version testing with no database
#
check: check-python-shells check-unittests

EPMT_TEST_ENV=PATH=${PWD}:${PATH} SLURM_JOB_USER=`whoami`

check-python-shells:
	@if [ -d /tmp/epmt ]; then echo "Directory /tmp/epmt exists! Hit return to remove it, Control-C to stop now."; read yesno; fi
	@rm -rf /tmp/epmt
	@echo "epmt-example.csh (tcsh)" ; env -i SLURM_JOB_ID=111 ${EPMT_TEST_ENV} /bin/tcsh -e epmt-example.csh
	@rm -rf /tmp/epmt
	@echo "epmt-example.sh (bash)" ; env -i SLURM_JOB_ID=222 ${EPMT_TEST_ENV} /bin/bash -Eeu epmt-example.sh
	@rm -rf /tmp/epmt
check-unittests:
	@echo; echo "Testing built-in unit tests..."
	@env -i PATH=${PWD}:${PATH} python3 -m unittest -v -f test.test_lib test.test_anysh test.test_submit test.test_misc test.test_query test.test_outliers test.test_db_schema
