.ONESHELL:

#OS_TARGET=centos-7
OS_TARGET=ubuntu
PAPIEX_VERSION?=2.3.14
PAPIEX_SRC?=../papiex-oss
PYTHON_VERSION=3.9.16
EPMT_VERSION=$(shell sed -n '/_version = /p' src/epmt/epmtlib.py | sed 's/ //g; s/,/./g; s/.*(\(.*\))/\1/')
EPMT_RELEASE=epmt-$(EPMT_VERSION)-$(OS_TARGET).tgz
EPMT_FULL_RELEASE=EPMT-release-$(EPMT_VERSION)-$(OS_TARGET).tgz
EPMT_PYTHON_FULL_RELEASE=epmt-$(EPMT_VERSION).tar.gz
PAPIEX_RELEASE=papiex-epmt-$(PAPIEX_VERSION)-$(OS_TARGET).tgz
#
SHELL=/bin/bash
CONDA_ACTIVATE = source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate
DOCKER_RUN:=docker -D run
DOCKER_BUILD:=docker -D build --no-cache -f
#DOCKER_BUILD:=docker -D build -f
DOCKER_RUN_OPTS:= -it 
PWD=$(shell pwd)


### ---- # this prints which target is being run. from percipio learning
#SHELL += -x
OLD_SHELL := $(SHELL)
SHELL = $(warning -------Building---------- $@)$(OLD_SHELL)
#SHELL = $(warning Building $@)$(OLD_SHELL)
### ----

#### ---- # this prints out env vars and their values, from percipio learning
##        # I am actually not convinced it did it's job...
#ifdef TRACE
#.PHONY: _trace _value
#_trace:; @$(MAKE) --no-print-directory TRACE= \
#      $(TRACE)='$$(warning TRACE $(TRACE))$(shell $(MAKE) TRACE=$(TRACE) _value)'
#_value: ; @echo '$(value $(TRACE))'
#endif
#### ----

.PHONY: default \\
	epmt-build epmt-test \\
	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3 check-integration-tests \\
	dist build compile lint release release6 release7 release-all \\
	install-py3-pyenv install-py3deps-pyenv
#	clean distclean \\

epmt-build compile build:
	@echo
	@echo "(MAKE TARG: epmt-build compile build) whoami"; whoami
	@echo
	cd src/epmt
	python3 -O -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py
lint:
	@echo
	@echo "(MAKE TARG: lint) whoami"; whoami
	@echo
	cd src/epmt
	python3 -m pylint -E *.py orm/*.py orm/*/*.py test/*.py

# install a virtual environment

install-py3-conda:
	@echo
	@echo "(MAKE TARG: install-py3-conda) whoami"; whoami
	@echo
	set -e; echo "Installing Python $(PYTHON_VERSION) using conda" ; \
	conda create -n $(EPMT_VERSION)_py$(PYTHON_VERSION) python=$(PYTHON_VERSION) -y ; \
	$(CONDA_ACTIVATE) $(EPMT_VERSION)_py$(PYTHON_VERSION) ; $(MAKE) install-deps ; \
	echo ; echo "Your virtual python environment is epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION)." ;

install-py3-pyenv:
	@echo
	@echo "(MAKE TARG: install-py3-pyenv) whoami"; whoami
	@echo
	set -e; echo "Installing Python $(PYTHON_VERSION) using pyenv"  
	PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install -s $(PYTHON_VERSION)  ; \
	pyenv virtualenv $(PYTHON_VERSION) epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION) ; \
	pyenv local epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION) ; $(MAKE) install-deps ; \
	echo ; echo "Your virtual python environment is epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION)." ;

install-deps:
	@echo
	@echo "(MAKE TARG: install-deps) whoami"; whoami
	@echo
	set -e ; pip install --upgrade pip ; pip install -r requirements.txt.py3 ; pip install -r src/epmt/ui/requirements-ui.txt.py3

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
	@echo
	@echo "(MAKE TARG: ${EPMT_RELEASE} dist) whoami"; whoami
	@echo
#	rm -rf epmt-install build
	mkdir -p epmt-install/epmt/epmtdocs
#	# activate venv if it exists, run pyinstaller in the
#	# same shell pipeline so it uses the venv (if activated)
#	# mkdocs also needs the same virtualenv, so includde it in the pipeline
#	# if [ -d .venv374 ]; then echo "activating virtualenv.."; source .venv374/bin/activate; fi; set -e; \
#	# [ "`python3 -V`" == "Python 3.7.4" ] || exit 1 ; 
	pyinstaller --clean --noconfirm --distpath=epmt-install epmt.spec
	mkdocs build -f epmtdocs/mkdocs.yml
#	# Rest of the commands below can be safely run outside the virtualenv
#	# resources
	cp -Rp preset_settings epmt-install
	cp -Rp notebooks epmt-install
	cp -Rp src/epmt/epmt_migrations epmt-install/migrations
	cp -pr src/epmt epmt-install
#	# examples
	mkdir epmt-install/examples 
	cp src/epmt/test/shell/epmt-example.*sh epmt-install/examples
#	# slurm
	mkdir epmt-install/slurm 
	cp SLURM/slurm_task_*log_epmt.sh epmt-install/slurm 
#	# docs
	cp -Rp epmtdocs/site epmt-install/epmt/epmtdocs
#	# release
	tar -czf $(EPMT_RELEASE) epmt-install
#	# ok enough of pyinstaller.  here's a pip-installable piece
	cd src
	tar zxf ../$(PAPIEX_RELEASE)
	python3 setup.py sdist
	chmod a+r dist/*

test-$(EPMT_RELEASE) dist-test:
	@echo
	@echo "(MAKE TARG: test-${EPMT_RELEASE} dist-test) whoami"; whoami
	@echo
# final location of tarfile
#	rm -rf epmt-install-tests && mkdir epmt-install-tests
	cp -Rp src/epmt/test epmt-install-tests
	tar -czf test-$(EPMT_RELEASE) epmt-install-tests
#	rm -rf epmt-install-tests

docker-dist: 
	@echo
	@echo "(MAKE TARG: docker-dist) whoami"; whoami
	@echo
	@echo " - building epmt and epmt-test tarball"
	@echo " - Dockerfile=Dockerfiles/Dockerfile.${OS_TARGET}-epmt-build"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build -t $(OS_TARGET)-epmt-build --progress plain --build-arg python_version=$(PYTHON_VERSION) .
	exit
#       # here this enters the image (container?) build above, and calls the pyinstaller steps at the $(EPMT_RELEASE) dist target
#	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) distclean dist dist-test
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) distclean dist dist-test

docker-dist-test:
	@echo
	@echo "(MAKE TARG: docker-dist-test) whoami"; whoami
	@echo
#	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) -it --rm --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) dist-test
#	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) -it --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) dist-test
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) -it --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) dist-test

papiex-dist: $(PAPIEX_RELEASE)
	@echo
	@echo "(MAKE TARG: papiex-dist) whoami"; whoami
	@echo

$(PAPIEX_RELEASE): $(PAPIEX_SRC)/$(PAPIEX_RELEASE)
	@echo
	@echo "(MAKE TARG: ${PAPIEX_RELEASE}) whoami"; whoami
	@echo
	cp $< $@

$(PAPIEX_SRC)/$(PAPIEX_RELEASE):
	@echo
	@echo "(MAKE TARG: ${PAPIEX_SRC}/${PAPIEX_RELEASE}) whoami"; whoami
	@echo
	make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) docker-dist
#	$(MAKE) -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) docker-dist 

epmt-full-release: $(EPMT_FULL_RELEASE)
	@echo
	@echo "(MAKE TARG: epmt-full-release) whoami"; whoami
	@echo

$(EPMT_FULL_RELEASE): $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE)
	@echo
	@echo "(MAKE TARG: ${EPMT_FULL_RELEASE}) whoami"; whoami
	@echo
	@echo "Making EPMT $(EPMT_VERSION) for $(OS_TARGET): $^"
	tar -cvzf $(EPMT_FULL_RELEASE) $(notdir $^)
	@echo
	@echo "$(EPMT_FULL_RELEASE) build complete!"
	@echo

check-release release-test-docker: $(EPMT_FULL_RELEASE)
	@echo
	@echo "(MAKE TARG: check-release release-test-docker) whoami"; whoami
	@echo
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test-release -t $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) --progress plain --build-arg epmt_version=$(EPMT_VERSION) --build-arg install_path=/opt/epmt --build-arg epmt_full_release=$(EPMT_PYTHON_FULL_RELEASE) .
	if docker ps | grep postgres-test > /dev/null; then docker stop postgres-test; fi
	if docker network ls | grep epmt-test-net > /dev/null; then docker network rm epmt-test-net; fi
	docker network create epmt-test-net
#	$(DOCKER_RUN) -d --rm --name postgres-test --network epmt-test-net -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT-TEST postgres:latest
	$(DOCKER_RUN) -d --name postgres-test --network epmt-test-net -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT-TEST postgres:latest
#	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net --privileged -it --rm -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:`; cp -fv $$install_prefix/epmt-$(EPMT_VERSION)/epmt-install/preset_settings/settings_test_pg_container.py $$install_prefix/epmt-$(EPMT_VERSION)/epmt-install/epmt/settings.py && epmt check && epmt unittest && epmt integration'
	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net --privileged -it -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; epmt -h| grep install_prefix|cut -f2 -d: ;install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:`; cp -fv $$install_prefix/epmt-$(EPMT_VERSION)/epmt-install/preset_settings/settings_test_pg_container.py $$install_prefix/epmt-$(EPMT_VERSION)/epmt-install/epmt/settings.py && epmt check && epmt unittest && epmt integration'
	docker stop postgres-test
	docker network rm epmt-test-net

release release-all release7:
	@echo
	@echo "(MAKE TARG: release release-all release7) whoami"; whoami
	@echo
	@echo "--- make distclean"
	$(MAKE) distclean
	@echo "--- make docker-dist"
	$(MAKE) docker-dist
	@echo "--- make epmt-full-release"
	$(MAKE) epmt-full-release
	@echo "--- make check-release"
	$(MAKE) check-release

#
#
#
clean:
	@echo
	@echo "(MAKE TARG: clean) whoami"; whoami
	@echo
	find . -type f \( -name "core" -or -name "*~" -or -name "*.pyc" -or -name "epmt.log" \)
	find . -type f \( -name "core" -or -name "*~" -or -name "*.pyc" -or -name "epmt.log" \) -exec rm -f {} \;
	rm -rf build epmt-install epmt-install-tests .venv374
	rm -rf src/epmt/ui/__pycache__ __pycache__

distclean: clean
	@echo
	@echo "(MAKE TARG: distclean) whoami"; whoami
	@echo
#	rm -rf src/epmt/ui/__pycache__ __pycache__
#	rm -rf build epmt-install epmt-install-tests .venv374
	rm -f settings.py $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE) $(EPMT_FULL_RELEASE)

nuke:
	@echo
	@echo "(MAKE TARG: nuke) whoami"; whoami
	@echo
	rm -f $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE) $(EPMT_FULL_RELEASE)
	rm -f src/dist/*
	rm -rf settings.py epmtdocs/site

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
