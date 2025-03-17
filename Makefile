.ONESHELL:

# OS and python
#PYTHON_VERSION=3.9.21
PYTHON_VERSION=3.9.16

#OS_TARGET=centos-7
OS_TARGET=rocky-8

# conda
CONDA_ACTIVATE = source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate

# docker run command
DOCKER_RUN:=docker -D run
#DOCKER_RUN:=docker run

# docker run opts
#DOCKER_RUN_OPTS:=--rm -it
DOCKER_RUN_OPTS:=-it

# docker build opts
#DOCKER_BUILD:=docker build --pull=false -f 
#DOCKER_BUILD:=docker -D build --pull=false -f 
#DOCKER_BUILD:=docker build -f 
#DOCKER_BUILD:=docker -D build -f
#DOCKER_BUILD:=docker build --no-cache -f
DOCKER_BUILD:=docker -D build --no-cache -f

# minimal-metrics src url for the epmt project- includes this repo, papiex, and epmt-dash (aka ui)
MM_SRC_URL_BASE=https://gitlab.com/minimal-metrics-llc/epmt

# papiex details
PAPIEX_VERSION?=2.3.14
PAPIEX_SRC?=papiex
#PAPIEX_SRC_BRANCH=master
#PAPIEX_SRC_BRANCH=centos7_yum_fix
PAPIEX_SRC_BRANCH=rocky8_docker
PAPIEX_SRC_TARBALL=papiex-epmt.tar.gz
PAPIEX_SRC_URL=$(MM_SRC_URL_BASE)/papiex/-/archive/$(PAPIEX_SRC_BRANCH)/$(PAPIEX_SRC_TARBALL)
PAPIEX_RELEASE=papiex-epmt-$(PAPIEX_VERSION)-$(OS_TARGET).tgz

# epmt details
EPMT_VERSION=$(shell sed -n '/_version = /p' src/epmt/epmtlib.py | sed 's/ //g; s/,/./g; s/.*(\(.*\))/\1/')
EPMT_RELEASE=epmt-$(EPMT_VERSION)-$(OS_TARGET).tgz
EPMT_FULL_RELEASE=EPMT-release-$(EPMT_VERSION)-$(OS_TARGET).tgz
EPMT_PYTHON_FULL_RELEASE=epmt-$(EPMT_VERSION).tar.gz
EPMT_INSTALL_PATH=/opt/minimalmetrics
EPMT_INSTALL_PREFIX=$(EPMT_INSTALL_PATH)/epmt-$(EPMT_VERSION)/epmt-install

# <root>/src/epmt/ui submodule details
EPMT_DASH_SRC_TARBALL=epmt-dash.tar.gz
EPMT_DASH_SRC_BRANCH=multi_page
EPMT_DASH_SRC_URL=$(MM_SRC_URL_BASE)/epmt-dash/-/archive/$(EPMT_DASH_SRC_BRANCH)/$(EPMT_DASH_SRC_TARBALL)
EPMT_DASH_SRC=src/epmt/ui

# shell
SHELL=/bin/bash
PWD=$(shell pwd)

# currently, these phony targets are not actually used.
.PHONY: default \\
	epmt-build epmt-test \\
	clean distclean \\
	check check-python-native check-python-driver \\
	check-python-2.6 check-python-2.7 \\
	check-python-3 check-integration-tests \\
	dist build compile lint \\
	release release6 release7 release-all \\
	install-py3-pyenv install-py3deps-pyenv

epmt-build compile build:
	@echo "(epmt-build compile build) whoami: $(shell whoami)"
	cd src/epmt
	python3 -O -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py

lint:
	@echo "(lint) whoami: $(shell whoami)"
	cd src/epmt
	python3 -m pylint -E *.py orm/*.py orm/*/*.py test/*.py

# install a virtual environment
install-py3-conda:
	@echo "(install-py3-conda) whoami: $(shell whoami)"
	set -e; echo "Installing Python $(PYTHON_VERSION) using conda" ; \
	conda create -n $(EPMT_VERSION)_py$(PYTHON_VERSION) python=$(PYTHON_VERSION) -y ; \
	$(CONDA_ACTIVATE) $(EPMT_VERSION)_py$(PYTHON_VERSION) ; $(MAKE) install-deps ; \
	echo ; echo "Your virtual python environment is epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION)." ;
install-py3-pyenv:
	@echo "(install-py3-pyenv) whoami: $(shell whoami)"
	set -e; echo "Installing Python $(PYTHON_VERSION) using pyenv"  
	PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install -s $(PYTHON_VERSION)  ; \
	pyenv virtualenv $(PYTHON_VERSION) epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION) ; \
	pyenv local epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION) ; $(MAKE) install-deps ; \
	echo ; echo "Your virtual python environment is epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION)." ;
install-deps:
	@echo "(install-deps) whoami: $(shell whoami)"
	set -e ; pip3 install --upgrade pip ; pip3 install -r requirements.txt.py3 ; \
	pip3 install -r src/epmt/ui/requirements-ui.txt.py3

# This target runs pyinstaller, outputs a tarball with
# epmt + all dependencies included
$(EPMT_RELEASE) dist:
	@echo "(EPMT_RELEASE dist) whoami: $(shell whoami)"
	@echo "WARNING removing directories: rm -rf epmt-install build"
	rm -rf epmt-install build
	@echo "DONE removing directories: rm -rf epmt-install build"
	mkdir -p epmt-install/epmt/epmtdocs
	@echo
	@echo
	@echo "**********************************************************"
	@echo "*************** calling pyinstaller **********************"
	@echo "**********************************************************"
	pyinstaller --version
#	remove the --clean flag to use the cache in builds, helps speed things up
	pyinstaller --clean --noconfirm --distpath=epmt-install epmt.spec
	@echo
	@echo
	@echo "**********************************************************"
	@echo "****************** calling mkdocs ************************"
	@echo "**********************************************************"
	mkdocs build -f epmtdocs/mkdocs.yml
	@echo
	@echo
	cp -Rp preset_settings epmt-install
	cp -Rp notebooks epmt-install
	cp -Rp src/epmt/epmt_migrations epmt-install/migrations
	cp -pr src/epmt epmt-install
#	examples
	mkdir epmt-install/examples 
	cp src/epmt/test/shell/epmt-example.*sh epmt-install/examples
#	slurm
	mkdir epmt-install/slurm 
	cp utils/SLURM/slurm_task_*log_epmt.sh epmt-install/slurm 
#	docs
	cp -Rp epmtdocs/site epmt-install/epmt/epmtdocs
	@echo
	@echo
	@echo "**********************************************************"
	@echo "************* creating ${EPMT_RELEASE} *******************"
	@echo "**********************************************************"
	tar -czf $(EPMT_RELEASE) epmt-install


python-dist: $(EPMT_RELEASE) $(PAPIEX_RELEASE)
	@echo "(python-dist) whoami: $(shell whoami)"
	@echo "**********************************************************"
	@echo "************** python3 setup.py sdist ********************"
	@echo "**********************************************************"	
	cd src && echo "GOOD: cd src" || echo "I FAILED: cd src"; \
	tar zxf ../$(PAPIEX_RELEASE) && echo "GOOD: tar -zxf ../PAPIEX_RELEASE" || echo "I FAILED: tar zxf ../PAPIEX_RELEASE"; \
	python3 setup.py sdist && echo "GOOD: python3 setup.py sdist" || echo "I FAILED: python3 setup.py sdist"; \
	chmod a+r dist/* && echo "GOOD: chmod a+r dist/*" || echo "I FAILED: chmod a+r dist/*"

test-$(EPMT_RELEASE) dist-test:
	@echo "(test-EPMT_RELEASE dist-test) whoami: $(shell whoami)"
	@echo
	@echo "WARNING recreating directories: rm -rf epmt-install-tests"
	rm -rf epmt-install-tests && mkdir epmt-install-tests
	@echo "DONE recreating directories: rm -rf epmt-install-tests"
	@echo
	cp -Rp src/epmt/test epmt-install-tests
	@echo "creating tarball in final location: test-${EPMT_RELEASE}"
	tar -czf test-$(EPMT_RELEASE) epmt-install-tests
	@echo
	@echo "WARNING removing directory: rm -rf epmt-install-tests"
	rm -rf epmt-install-tests
	@echo "WARNING recreating directories: rm -rf epmt-install-tests"

docker-dist:
	@echo " ------ CREATE EPMT TARBALL: docker-dist ------- "
	@echo "       build command = ${DOCKER_BUILD}"
	@echo "       run   command = ${DOCKER_RUN}"
	@echo "       run   options = ${DOCKER_RUN_OPTS}"
	@echo "(docker-dist) whoami: $(shell whoami)"
	@echo
	@echo
	@echo " - building epmt and epmt-test tarball via Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build -t $(OS_TARGET)-epmt-build:$(EPMT_VERSION) \
	--build-arg python_version=$(PYTHON_VERSION) .
	@echo
	@echo
	@echo " - running make dist python-dist dist-test inside $(OS_TARGET)-epmt-build"
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --privileged --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build:$(EPMT_VERSION) \
	make --debug OS_TARGET=$(OS_TARGET) dist python-dist $(EPMT_RELEASE) dist-test


docker-dist-test:
	@echo "(docker-dist-test) whoami: $(shell whoami)"
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --privileged --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build:$(EPMT_VERSION) \
	make --debug OS_TARGET=$(OS_TARGET) dist-test

epmt-dash: $(EPMT_DASH_SRC)
	@echo "(epmt-dash) whoami: $(shell whoami)"

$(EPMT_DASH_SRC): $(EPMT_DASH_SRC_TARBALL)
	@echo "(EPMT_DASH_SRC) whoami: $(shell whoami)"
	@echo " ------ GRAB EPMT-DASH SUBODULE (UI) ------- "
	@echo   "EPMT_DASH_SRC_TARBALL = ${EPMT_DASH_SRC_TARBALL}"
	@echo   "EPMT_DASH_SRC_BRANCH  = ${EPMT_DASH_SRC_BRANCH}"
	@echo   "EPMT_DASH_SRC_URL     = ${EPMT_DASH_SRC_URL}"
	@echo
	@echo
	echo "untarring ${EPMT_DASH_SRC_TARBALL}"; \
	tar zxf $(EPMT_DASH_SRC_TARBALL); \
	mv `tar ztf ${EPMT_DASH_SRC_TARBALL} | head -1` $(EPMT_DASH_SRC); \
	echo "top-level dir contents of EPMT_DASH_SRC=${EPMT_DASH_SRC}..."; \
	ls $(EPMT_DASH_SRC); \
	echo "making symbolic link to epmt/ui/docs/index.md"; \
	cd epmtdocs/docs && \
	ln -s ../../src/epmt/ui/docs/index.md index.md || \
	echo "symbolic link creation failed."; \
	cd -

$(EPMT_DASH_SRC_TARBALL):
	@echo "(EPMT_DASH_SRC_TARBALL) whoami: $(shell whoami)"
	echo "grabbing epmt-dash via curl"; \
	curl -O $(EPMT_DASH_SRC_URL); \
	ls $(EPMT_DASH_SRC_TARBALL); \



papiex-dist: $(PAPIEX_RELEASE)
	@echo "(papiex-dist) whoami: $(shell whoami)"

$(PAPIEX_RELEASE): $(PAPIEX_SRC)/$(PAPIEX_RELEASE)
	@echo "(PAPIEX_RELEASE) whoami: $(shell whoami)"
	cp $< $@

$(PAPIEX_SRC)/$(PAPIEX_RELEASE): $(PAPIEX_SRC)
	@echo "(PAPIEX_SRC/PAPIEX_RELEASE) whoami: $(shell whoami)"
	@echo " ------ CREATE PAPIEX TARBALL : papiex-dist ------- "
	- @echo "PAPIEX_VERSION     = ${PAPIEX_VERSION}"
	- @echo "PAPIEX_SRC         = ${PAPIEX_SRC}"
	@echo   "PAPIEX_SRC_TARBALL = ${PAPIEX_SRC_TARBALL}"
	@echo   "PAPIEX_SRC_BRANCH  = ${PAPIEX_SRC_BRANCH}"
	@echo   "PAPIEX_SRC_URL     = ${PAPIEX_SRC_URL}"
	- @echo   "PAPIEX_RELEASE     = ${PAPIEX_RELEASE}"
	@echo
	@echo
	@echo "################### BEGIN MAKE PAPIEX TARBALL : papiex-dist ########################################"
	if [ -n "${OUTSIDE_DOCKER}" ]; then \
	echo "making distclean install dist within PAPIEX_SRC/PAPIEX_RELEASE target"; \
	make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) distclean install dist; \
	echo "################# DONE making docker-dist within PAPIEX_SRC/PAPIEX_RELEASE target ########################"; \
	else \
	echo "making docker-dist within PAPIEX_SRC/PAPIEX_RELEASE target"; \
	make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) docker-dist; \
	echo "################# DONE making docker-dist within PAPIEX_SRC/PAPIEX_RELEASE target ########################"; \
	fi
	@echo "################### DONE MAKE PAPIEX TARBALL : papiex-dist ########################################"

$(PAPIEX_SRC): $(PAPIEX_SRC_TARBALL)
	@echo "(PAPIEX_SRC) whoami: $(shell whoami)"
	ls $(PAPIEX_SRC_TARBALL); \
	echo "tar zxf ${PAPIEX_SRC_TARBALL}"; \
	tar zxf $(PAPIEX_SRC_TARBALL); \
	mv `tar ztf ${PAPIEX_SRC_TARBALL} | head -1` $(PAPIEX_SRC); \
	echo "top-level dir contents of PAPIEX_SRC=${PAPIEX_SRC}..."; \
	ls $(PAPIEX_SRC); \

$(PAPIEX_SRC_TARBALL):
	@echo "(PAPIEX_SRC_TARBALL) whoami: $(shell whoami)"
	curl -O $(PAPIEX_SRC_URL); \
	ls $(PAPIEX_SRC_TARBALL)

epmt-full-release: $(EPMT_FULL_RELEASE)
	@echo "(epmt-full-release) whoami: $(shell whoami)"

$(EPMT_FULL_RELEASE): $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE)
	@echo "(EPMT_FULL_RELEASE) whoami: $(shell whoami)"
	@echo "Making EPMT $(EPMT_VERSION) for $(OS_TARGET): $^"
	tar -cvzf $(EPMT_FULL_RELEASE) $(notdir $^)
	@echo
	@echo "$(EPMT_FULL_RELEASE) build complete!"
	@echo

check-release release-test-docker: $(EPMT_FULL_RELEASE)
	@echo "(check-release release-test-docker) whoami: $(shell whoami)"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test-release \
	-t $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) \
	--build-arg epmt_version=$(EPMT_VERSION) --build-arg install_path=$(EPMT_INSTALL_PATH) \
	--build-arg install_prefix=$(EPMT_INSTALL_PREFIX) --build-arg epmt_full_release=$(EPMT_FULL_RELEASE) \
	--build-arg epmt_python_full_release=$(EPMT_PYTHON_FULL_RELEASE) \
	--build-arg python_version=$(PYTHON_VERSION) .
	@echo
	@echo
	@echo "looking for postgres-test and epmt-test-net docker networks"
	if docker ps | grep postgres-test > /dev/null; \
	then docker stop postgres-test; fi
	@echo
	@echo
	if docker network ls | grep epmt-test-net > /dev/null; \
	then docker network rm -f epmt-test-net; fi
	@echo
	@echo
	@echo "creating epmt-test-net docker network"
	docker network create epmt-test-net
	@echo
	@echo
	@echo "running postgres-test container"
	$(DOCKER_RUN) -d --rm --name postgres-test --network epmt-test-net \
	--privileged -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT-TEST postgres:latest
	@echo
	@echo
	@echo "running epmt-test-release container"
	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net \
	--privileged $(DOCKER_RUN_OPTS) -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) \
	bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; epmt -v -V; \
	echo "" && echo "------ epmt -v check ------" && epmt -v -v check; \
	echo "" && echo "------ epmt -v unittest ------" && epmt -v -v unittest; \
	echo "" && echo "------ epmt -v integration ------" && epmt -v -v integration; \
	echo "" && echo "------ DONE WITH EPMT CHECKS ------"'
	@echo
	@echo
	@echo "shutting down docker networks, postgres test container, epmt-test-net"
	docker stop postgres-test
	docker network rm -f epmt-test-net


# release building
release release-all release7:
	@echo "(release release-all release7) whoami: $(shell whoami)"
	@echo
	@echo
	@echo " ------ MAKE : clean-all / CLEAN ------- "
	$(MAKE) clean-all
	@echo
	@echo
	@echo " ------ MAKE : epmt-dash / DASH ------- "
	$(MAKE) epmt-dash
	@echo
	@echo
	@echo " ------ MAKE : papiex-dist / PAPIEX ------- "
	$(MAKE) papiex-dist
	@echo
#	@echo
#	@echo " ------ MAKE : docker-dist / DIST ------- "
#	$(MAKE) docker-dist
#	@echo
#	@echo
#	@echo " ------ MAKE : epmt-full-release / FULL-RELEASE ------- "
#	$(MAKE) epmt-full-release
#	@echo
# 	@echo
#	@echo " ------ MAKE : check-release / CHECK-RELEASE ------- "
#	$(MAKE) check-release
#	@echo
#	@echo "done building epmt"



# CLEANING
extra-clean: clean-all papiexclean dashclean
	@echo "(extra-clean) whoami: $(shell whoami)"

clean-all: clean distclean docker-clean 
	@echo "(clean-all) whoami: $(shell whoami)"

clean:
	@echo "(clean) whoami: $(shell whoami)"
	- find . -type f \( -name "core" -or -name "*~" -or -name "*.pyc" -or -name "epmt.log" \) -exec rm -f {} \;
	- rm -rf src/epmt/ui/__pycache__ __pycache__ build epmt-install epmt-install-tests .venv374

distclean:
	@echo "(distclean) whoami: $(shell whoami)"
	- rm -f settings.py $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(EPMT_FULL_RELEASE) src/dist/*
	- rm -rf epmtdocs/site 

dashclean:
	@echo "(distclean) whoami: $(shell whoami)"
	- rm -rf $(EPMT_DASH_SRC)
	- rm -f $(EPMT_DASH_SRC_TARBALL)
	- rm -f epmtdocs/docs/index.md

docker-clean:
	@echo "(docker-clean) whoami: $(shell whoami)"
	- docker image rm --force \
	$(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) $(OS_TARGET)-epmt-build:$(EPMT_VERSION)


clean-papiex: papiexclean
	@echo "(clean-papiex) whoami: $(shell whoami)"

papiexclean:
	@echo "(papiexclean) whoami: $(shell whoami)"
	- rm -fr $(PAPIEX_SRC) 
	- rm -f $(PAPIEX_SRC_TARBALL) $(PAPIEX_RELEASE)



# Simple python version testing with no database
# We should get rid of this in favor of a sequence of epmt commands.
check: check-epmt-check check-integration-tests check-unittests
	@echo "(check) whoami: $(shell whoami)"

# Why not test all of them?
check-epmt-check:
	@echo "(check-epmt-check) whoami: $(shell whoami)"
	- @env -i TERM=ansi PATH=${PWD}:${PATH} epmt -v -v check
check-integration-tests:
	@echo "(check-integration-tests) whoami: $(shell whoami)"
	- @env -i TERM=ansi PATH=${PWD}:${PATH} epmt -v -v integration
check-unittests:
	@echo "(check-unittests) whoami: $(shell whoami)"
	- @env -i TERM=ansi PATH=${PWD}:${PATH} epmt -v -v unittest
#	@env -i TERM=ansi PATH=${PWD}:${PATH} python3 -m unittest -v -f \
#   test.test_lib test.test_stat test.test_settings \
#	test.test_anysh test.test_submit test.test_run \
#	test.test_cmds test.test_query test.test_explore \
#	test.test_outliers test.test_db_schema test.test_db_migration
