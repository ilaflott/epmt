OS_TARGET=centos-7
PAPIEX_VERSION?=2.3.14
PAPIEX_SRC?=../papiex
PYTHON_VERSION=3.9.16
EPMT_VERSION=$(shell sed -n '/_version = /p' epmtlib.py | sed 's/ //g; s/,/./g; s/.*(\(.*\))/\1/')
EPMT_RELEASE=epmt-$(EPMT_VERSION)-$(OS_TARGET).tgz
EPMT_FULL_RELEASE=EPMT-release-$(EPMT_VERSION)-$(OS_TARGET).tgz
PAPIEX_RELEASE=papiex-epmt-$(PAPIEX_VERSION)-$(OS_TARGET).tgz
#
SHELL=/bin/bash
DOCKER_RUN:=docker run
DOCKER_BUILD:=docker build -f
DOCKER_RUN_OPTS:=--rm -it
PWD=$(shell pwd)

.PHONY: default \\
	epmt-build epmt-test \\
	clean distclean \\
	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3 check-integration-tests\\
	dist build compile lint release release6 release7 release-all

epmt-build compile build:
	python3 -O -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py
lint:
	python3 -m pylint -E *.py orm/*.py orm/*/*.py test/*.py

# install python3.7.4 if it's not already installed
# Also, if needed install a virtual environment in .venv374
install-py3:
	@if [ "`python3 -V`" != "$(PYTHON_VERSION)" ]; then \
		set -e; echo "Installing Python $(PYTHON_VERSION) using pyenv" ; \
		which pyenv > /dev/null || curl https://pyenv.run | bash ; \
		PATH="$$HOME/.pyenv/bin:$$PATH" ; \
		eval "$$(pyenv init -)" ; \
		eval "$$(pyenv virtualenv-init -)" ; \
		pyenv versions ; \
		PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install -s $(PYTHON_VERSION) ; \
		pyenv shell $(PYTHON_VERSION) ; \
		python3 -V ; \
	fi ; 

#rm -rf .venv374 ; \
#	if python3 -m epmt_query 2>&1| grep ModuleNotFound > /dev/null; then \
#		set -e; echo "Setting up a virtual environment (in .venv374).." ; \
#		[ -d .venv374 ] || python3 -m venv .venv374 ; \
#		source .venv374/bin/activate; set -e ; \
#		pip3 install --upgrade pip ; \
#		pip3 install -r requirements.txt.py3 ; \
#		pip3 install -r ui/requirements-ui.txt.py3 ; \
#	fi

# This target runs pyinstaller to produce an epmt tarball that
# has all the dpeendencies included.
# If a virtual environment is found in .venv374 then use it
# Otherwise, assume the environment is already ready to run
# pyinstaller.
$(EPMT_RELEASE) dist:
	$(MAKE) install-py3
	rm -rf epmt-install build
	mkdir -p epmt-install/epmt/epmtdocs
	# activate venv if it exists, run pyinstaller in the
	# same shell pipeline so it uses the venv (if activated)
	# mkdocs also needs the same virtualenv, so includde it in the pipeline
	if [ -d .venv374 ]; then echo "activating virtualenv.."; source .venv374/bin/activate; fi; set -e; \
	[ "`python3 -V`" == "Python 3.7.4" ] || exit 1 ; \
	pyinstaller --clean --noconfirm --distpath=epmt-install epmt.spec ; \
	mkdocs build -f epmtdocs/mkdocs.yml
	# Rest of the commands below can be safely run outside the virtualenv
	# resources
	cp -Rp preset_settings epmt-install
	cp -Rp notebooks epmt-install
	cp -Rp migrations epmt-install
	cp -p alembic.ini epmt-install
	# examples
	mkdir epmt-install/examples 
	cp test/shell/epmt-example.*sh epmt-install/examples
	# slurm
	mkdir epmt-install/slurm 
	cp SLURM/slurm_task_*log_epmt.sh epmt-install/slurm 
	# docs
	cp -Rp epmtdocs/site epmt-install/epmt/epmtdocs
	# release
	tar -czf $(EPMT_RELEASE) epmt-install 

test-$(EPMT_RELEASE) dist-test:
# final location of tarfile
	rm -rf epmt-install-tests && mkdir epmt-install-tests
	cp -Rp test epmt-install-tests
	tar -czf test-$(EPMT_RELEASE) epmt-install-tests
	rm -rf epmt-install-tests

docker-dist: 
	@echo " - building epmt and epmt-test tarball"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build -t $(OS_TARGET)-epmt-build .
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) distclean dist dist-test

docker-dist-test:
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) -it --rm --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) dist-test

papiex-dist: $(PAPIEX_RELEASE)

$(PAPIEX_RELEASE): $(PAPIEX_SRC)/$(PAPIEX_RELEASE)
	cp $< $@

$(PAPIEX_SRC)/$(PAPIEX_RELEASE):
	make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) docker-dist 

epmt-full-release: $(EPMT_FULL_RELEASE)

$(EPMT_FULL_RELEASE): $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE)
	@echo "Making EPMT $(EPMT_VERSION) for $(OS_TARGET): $^"
	tar -cvzf $(EPMT_FULL_RELEASE) $(notdir $^)
	@echo
	@echo "$(EPMT_FULL_RELEASE) build complete!"
	@echo

check-release release-test-docker: $(EPMT_FULL_RELEASE)
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test-release -t $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) --build-arg epmt_version=$(EPMT_VERSION) --build-arg install_path=/opt/minimalmetrics --build-arg epmt_full_release=$(EPMT_FULL_RELEASE) .
	if docker ps | grep postgres-test > /dev/null; then docker stop postgres-test; fi
	if docker network ls | grep epmt-test-net > /dev/null; then docker network rm epmt-test-net; fi
	docker network create epmt-test-net
	$(DOCKER_RUN) -d --rm --name postgres-test --network epmt-test-net -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT-TEST postgres:latest
	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net --privileged -it --rm -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:`; cp -fv $$install_prefix/../epmt-install/preset_settings/settings_test_pg_container.py $$install_prefix/../epmt-install/epmt/settings.py && epmt check && epmt unittest && epmt integration'
	docker stop postgres-test
	docker network rm epmt-test-net

release release-all release7:
	$(MAKE) distclean
	$(MAKE) docker-dist
	$(MAKE) epmt-full-release
	$(MAKE) check-release

#
#
#
clean:
	find . -type f \( -name "core" -or -name "*~" -or -name "*.pyc" -or -name "epmt.log" \) -exec rm -f {} \;
	rm -rf ui/__pycache__ __pycache__ build epmt-install epmt-install-tests .venv374ß

distclean: clean
	rm -f settings.py $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE) $(EPMT_FULL_RELEASE)
	rm -rf epmtdocs/site

# 
# Simple python version testing with no database
#

# We should get rid of this in favor of a sequence of epmt commands.

check: check-unittests check-integration-tests

check-unittests: # Why not test all of them?
	@env -i TERM=ansi PATH=${PWD}:${PATH} epmt unittest
#@env -i TERM=ansi PATH=${PWD}:${PATH} python3 -m unittest -v -f test.test_lib test.test_stat test.test_settings test.test_anysh test.test_submit test.test_run test.test_cmds test.test_query test.test_explore test.test_outliers test.test_db_schema test.test_db_migration
check-integration-tests:
	@env -i TERM=ansi PATH=${PWD}:${PATH} epmt integration
