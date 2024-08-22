.ONESHELL:

# OS and python
PYTHON_VERSION=3.9.16
OS_TARGET=centos-7

# conda
CONDA_ACTIVATE = source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate

# docker commands
#DOCKER_RUN:=docker run
DOCKER_RUN:=docker -D run
#DOCKER_RUN_OPTS:=--rm -it
DOCKER_RUN_OPTS:=-it
#DOCKER_BUILD:=docker build -f
#DOCKER_BUILD:=docker -D build -f
DOCKER_BUILD:=docker -D build --no-cache -f

# papiex details
PAPIEX_VERSION?=2.3.14
PAPIEX_SRC?=papiex
PAPIEX_SRC_BRANCH=epmt
PAPIEX_SRC_TARBALL=papiex-${PAPIEX_SRC_BRANCH}.tar.gz
PAPIEX_SRC_URL=https://gitlab.com/minimal-metrics-llc/epmt/papiex/-/archive/master/${PAPIEX_SRC_TARBALL}
PAPIEX_RELEASE=papiex-epmt-$(PAPIEX_VERSION)-$(OS_TARGET).tgz

# epmt details
EPMT_VERSION=$(shell sed -n '/_version = /p' src/epmt/epmtlib.py | sed 's/ //g; s/,/./g; s/.*(\(.*\))/\1/')
EPMT_RELEASE=epmt-$(EPMT_VERSION)-$(OS_TARGET).tgz
EPMT_FULL_RELEASE=EPMT-release-$(EPMT_VERSION)-$(OS_TARGET).tgz
EPMT_PYTHON_FULL_RELEASE=epmt-$(EPMT_VERSION).tar.gz

# shell
SHELL=/bin/bash
PWD=$(shell pwd)
# uncomment below two for helpful output
#OLD_SHELL:=$(SHELL)
#SHELL=$(warning ------- TARGET is -- $@ -- )$(OLD_SHELL)


.PHONY: default \\
	epmt-build epmt-test \\
	clean distclean \\
	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3 check-integration-tests\\
	dist build compile lint release release6 release7 release-all \\
	install-py3-pyenv install-py3deps-pyenv

epmt-build compile build:
	@echo "(STEP  ) whoami: $(shell whoami)"
	cd src/epmt
	python3 -O -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py

lint:
	@echo "(STEP  ) whoami: $(shell whoami)"
	cd src/epmt
	python3 -m pylint -E *.py orm/*.py orm/*/*.py test/*.py

# install a virtual environment

install-py3-conda:
	@echo "(STEP  ) whoami: $(shell whoami)"
	set -e; echo "Installing Python $(PYTHON_VERSION) using conda" ; \
	conda create -n $(EPMT_VERSION)_py$(PYTHON_VERSION) python=$(PYTHON_VERSION) -y ; \
	$(CONDA_ACTIVATE) $(EPMT_VERSION)_py$(PYTHON_VERSION) ; $(MAKE) install-deps ; \
	echo ; echo "Your virtual python environment is epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION)." ;
install-py3-pyenv:
	@echo "(STEP  ) whoami: $(shell whoami)"
	set -e; echo "Installing Python $(PYTHON_VERSION) using pyenv"  
	PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install -s $(PYTHON_VERSION)  ; \
	pyenv virtualenv $(PYTHON_VERSION) epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION) ; \
	pyenv local epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION) ; $(MAKE) install-deps ; \
	echo ; echo "Your virtual python environment is epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION)." ;
install-deps:
	@echo "(STEP  ) whoami: $(shell whoami)"
	set -e ; pip3 install --upgrade pip ; pip3 install -r requirements.txt.py3 ; pip3 install -r src/epmt/ui/requirements-ui.txt.py3

# This target runs pyinstaller to produce an epmt tarball that
# has all the dpeendencies included.
# If a virtual environment is found in .venv374 then use it
# Otherwise, assume the environment is already ready to run
# pyinstaller.
$(EPMT_RELEASE) dist:
	@echo "(STEP 6) whoami: $(shell whoami)"
	rm -rf epmt-install build
	mkdir -p epmt-install/epmt/epmtdocs
	pyinstaller --version
#	remove the --clean flag to use the cache in builds, helps speed things up
#	pyinstaller --noconfirm --distpath=epmt-install epmt.spec
	pyinstaller --clean --noconfirm --distpath=epmt-install epmt.spec
#       mkdocs sooooo slow
	mkdocs build -f epmtdocs/mkdocs.yml
#	mkdocs build --dirty -f epmtdocs/mkdocs.yml
	cp -Rp preset_settings epmt-install
	cp -Rp notebooks epmt-install
	cp -Rp src/epmt/epmt_migrations epmt-install/migrations
	cp -pr src/epmt epmt-install
	# examples
	mkdir epmt-install/examples 
	cp src/epmt/test/shell/epmt-example.*sh epmt-install/examples
	# slurm
	mkdir epmt-install/slurm 
	cp SLURM/slurm_task_*log_epmt.sh epmt-install/slurm 
	# docs
	cp -Rp epmtdocs/site epmt-install/epmt/epmtdocs
	# release
	tar -czf $(EPMT_RELEASE) epmt-install


#python-dist: $(EPMT_RELEASE)
python-dist: $(EPMT_RELEASE) $(PAPIEX_RELEASE)
	@echo "(STEP 7 i think) whoami: $(shell whoami)"
	cd src
	tar zxf ../$(PAPIEX_RELEASE)
	python3 setup.py sdist
	chmod a+r dist/*

test-$(EPMT_RELEASE) dist-test:
	@echo "(STEP 8) whoami: $(shell whoami)"
# final location of tarfile
	rm -rf epmt-install-tests && mkdir epmt-install-tests
	cp -Rp src/epmt/test epmt-install-tests
	tar -czf test-$(EPMT_RELEASE) epmt-install-tests
	rm -rf epmt-install-tests

docker-dist:
	@echo "(STEP 5) whoami: $(shell whoami)"
	@echo " - building epmt and epmt-test tarball via Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build -t $(OS_TARGET)-epmt-build:$(EPMT_VERSION) --build-arg python_version=$(PYTHON_VERSION) .
	@echo " - running make dist python-dist dist-test inside $(OS_TARGET)-epmt-build"
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build:$(EPMT_VERSION) make OS_TARGET=$(OS_TARGET)  dist python-dist $(EPMT_RELEASE) dist-test
#	@echo " - running make papiex-dist python-dist dist-test inside $(OS_TARGET)-epmt-build"
#	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build:$(EPMT_VERSION) make OS_TARGET=$(OS_TARGET)  papiex-dist python-dist $(EPMT_RELEASE) dist-test


docker-dist-test:
	@echo "(STEP  ) whoami: $(shell whoami)"
#	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) -it --rm --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build:$(EPMT_VERSION)  make OS_TARGET=$(OS_TARGET) dist-test
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build:$(EPMT_VERSION)  make OS_TARGET=$(OS_TARGET) dist-test

papiex-dist: $(PAPIEX_RELEASE)
	@echo "(STEP 12 i think) whoami: $(shell whoami)"

$(PAPIEX_RELEASE): $(PAPIEX_SRC)/$(PAPIEX_RELEASE)
	@echo "(STEP 11 i think) whoami: $(shell whoami)"
	cp $< $@

$(PAPIEX_SRC)/$(PAPIEX_RELEASE):
	@echo "(STEP 10 i think) whoami: $(shell whoami)"
	@echo "PAPIEX_SRC         is ${PAPIEX_SRC}"
	@echo "PAPIEX_SRC_URL     is ${PAPIEX_SRC_URL}"
	@echo "PAPIEX_SRC_TARBALL is ${PAPIEX_SRC_TARBALL}"
	if [ ! -d $(PAPIEX_SRC) ]; then \
	echo "grabbing papiex via curl"; \
	curl -O ${PAPIEX_SRC_URL}; \
	ls $(PAPIEX_SRC_TARBALL); \
	echo "tar zxf PAPIEX_SRC_TARBALL=${PAPIEX_SRC_TARBALL}... listing below this line"; \
	tar zxf ${PAPIEX_SRC_TARBALL}; \
	mv `tar ztf ${PAPIEX_SRC_TARBALL} | head -1` $(PAPIEX_SRC); \
	echo "listing contents of PAPIEX_SRC_TARBALL=${PAPIEX_SRC_TARBALL}..."; \
	echo "aka... top dir contents of PAPIEX_SRC=${PAPIEX_SRC}..."; \
	ls $(PAPIEX_SRC); \
	fi
	if [ -n "${OUTSIDE_DOCKER}" ]; \
	then make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) distclean install dist; \
	else \
	echo "making docker-dist within PAPIEX_SRC/PAPIEX_RELEASE target"; \
	make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) docker-dist; \
	fi

epmt-full-release: $(EPMT_FULL_RELEASE)
	@echo "(STEP 14) whoami: $(shell whoami)"

$(EPMT_FULL_RELEASE): $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE)
	@echo "(STEP 13) whoami: $(shell whoami)"
	@echo "Making EPMT $(EPMT_VERSION) for $(OS_TARGET): $^"
	tar -cvzf $(EPMT_FULL_RELEASE) $(notdir $^)
	@echo
	@echo "$(EPMT_FULL_RELEASE) build complete!"
	@echo

check-release release-test-docker: $(EPMT_FULL_RELEASE)
	@echo "(STEP 15) whoami: $(shell whoami)"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test-release -t $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) --build-arg epmt_version=$(EPMT_VERSION) --build-arg install_path=/opt/minimalmetrics --build-arg epmt_full_release=$(EPMT_FULL_RELEASE) --build-arg epmt_python_full_release=$(EPMT_PYTHON_FULL_RELEASE)  --build-arg python_version=$(PYTHON_VERSION) .
	@echo "looking for postgres-test and epmt-test-net docker networks"
	if docker ps | grep postgres-test > /dev/null; then docker stop postgres-test; fi
	if docker network ls | grep epmt-test-net > /dev/null; then docker network rm epmt-test-net; fi
	@echo "creating epmt-test-net docker network"
	docker network create epmt-test-net
	@echo "running postgres-test container"
	$(DOCKER_RUN) -d --rm --name postgres-test --network epmt-test-net -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT-TEST postgres:latest
	@echo "running epmt-test-release container"
#	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net --privileged -it --rm -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:|sed 's/papiex-//'`; cp -fv $$install_prefix/preset_settings/settings_test_pg_container.py $$install_prefix/settings.py && epmt check && epmt unittest && epmt integration'
#	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net --privileged $(DOCKER_RUN_OPTS) -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:|sed 's/papiex-//'`; cp -fv $$install_prefix/preset_settings/settings_test_pg_container.py $$install_prefix/settings.py && epmt check && epmt unittest && epmt integration'
	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net --privileged $(DOCKER_RUN_OPTS) -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:|sed 's/papiex-epmt-install/epmt-install/'`; ls $${install_prefix}preset_settings/settings_test_pg_container.py; cp -fv $${install_prefix}preset_settings/settings_test_pg_container.py $${install_prefix}epmt/settings.py; ls $${install_prefix}epmt/settings.py; epmt check && epmt unittest && epmt integration'
	@echo "shutting down docker networks, postgres test container, epmt-test-net"
	docker stop postgres-test
	docker network rm epmt-test-net


# release building
release release-all release7:
#	@echo "(STEP 1) whoami: $(shell whoami)"
#	@echo " ------ MAJOR STEP 1: clean-all ------- "
#	$(MAKE) clean-all
	@echo " ------ MAJOR STEP 2: papiex-dist ------- "
	$(MAKE) papiex-dist
	@echo " ------ MAJOR STEP 3: docker-dist ------- "
	$(MAKE) docker-dist
	@echo " ------ MAJOR STEP 4: epmt-full-release ------- "
	$(MAKE) epmt-full-release
	@echo " ------ MAJOR STEP 5: check-release ------- "
	$(MAKE) check-release



# CLEANING
#clean-all: clean distclean docker-clean papiexclean
clean-all: clean distclean docker-clean
	@echo "(STEP 2) whoami: $(shell whoami)"
clean-papiex: papiexclean
	@echo "(STEP ?) whoami: $(shell whoami)"

clean:
	@echo "(STEP 2) whoami: $(shell whoami)"
	find . -type f \( -name "core" -or -name "*~" -or -name "*.pyc" -or -name "epmt.log" \) -exec rm -f {} \;
	rm -rf src/epmt/ui/__pycache__ __pycache__ build epmt-install epmt-install-tests .venv374

papiexclean:
	rm -fr $(PAPIEX_SRC)
	rm -f $(PAPIEX_SRC_TARBALL) $(PAPIEX_RELEASE)

distclean:
	@echo "(STEP 3) whoami: $(shell whoami)"
	rm -f settings.py $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(EPMT_FULL_RELEASE) src/dist/*
	rm -rf epmtdocs/site

docker-clean:
	@echo "(STEP 4) whoami: $(shell whoami)"
	- docker image rm --force $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) $(OS_TARGET)-epmt-build:$(EPMT_VERSION) 


# Simple python version testing with no database
# We should get rid of this in favor of a sequence of epmt commands.
check: check-unittests check-integration-tests
	@echo "(STEP  ) whoami: $(shell whoami)"

# Why not test all of them?
check-unittests:
	@echo "(STEP  ) whoami: $(shell whoami)"
	@env -i TERM=ansi PATH=${PWD}:${PATH} epmt unittest
#@env -i TERM=ansi PATH=${PWD}:${PATH} python3 -m unittest -v -f test.test_lib test.test_stat test.test_settings test.test_anysh test.test_submit test.test_run test.test_cmds test.test_query test.test_explore test.test_outliers test.test_db_schema test.test_db_migration
check-integration-tests:
	@echo "(STEP  ) whoami: $(shell whoami)"
	@env -i TERM=ansi PATH=${PWD}:${PATH} epmt integration
