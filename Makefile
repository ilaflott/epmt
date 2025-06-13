.ONESHELL:

# OS / python / SQLITE_VERSION
#OS_TARGET=centos-7
OS_TARGET=rocky-8

#PYTHON_VERSION=3.9.16
#PYTHON_VERSION=3.9.21
PYTHON_VERSION=3.9.22

#SQLITE_YEAR=2023
#SQLITE_VERSION=3430100
SQLITE_YEAR=2025
SQLITE_VERSION=3490100


# conda
CONDA_ACTIVATE = source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate ;

# docker run command
#DOCKER_RUN:=docker -D run
DOCKER_RUN:=docker run

# docker run opts
#DOCKER_RUN_OPTS:=--rm -it
DOCKER_RUN_OPTS:=-it

# docker build opts
#DOCKER_BUILD:=docker build --pull=false -f 
#DOCKER_BUILD:=docker -D build --pull=false -f

DOCKER_BUILD:=docker build -f 
#DOCKER_BUILD:=docker -D build -f

#DOCKER_BUILD:=docker build --no-cache -f
#DOCKER_BUILD:=docker -D build --no-cache -f

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
#INL_SRC_URL_BASE=https://github.com/ilaflott
#EPMT_DASH_SRC_BRANCH=main
#EPMT_DASH_SRC_TARBALL=epmt-dash-$(EPMT_DASH_SRC_BRANCH).tar.gz
#EPMT_DASH_SRC_URL=$(INL_SRC_URL_BASE)/epmt-dash/archive/refs/heads/$(EPMT_DASH_SRC_TARBALL)
EPMT_DASH_SRC_TARBALL=epmt-dash.tar.gz
EPMT_DASH_SRC_BRANCH=multi_page
EPMT_DASH_SRC_URL=$(MM_SRC_URL_BASE)/epmt-dash/-/archive/$(EPMT_DASH_SRC_BRANCH)/$(EPMT_DASH_SRC_TARBALL)
EPMT_DASH_SRC=src/epmt/ui
#EPMT_DASH_SRC=ui

## other details
#PYINSTALLER_DIST_DIR=epmt-install # does this make sense???

# shell
SHELL=/bin/bash
PWD=$(shell pwd)

.PHONY: default \\
	epmt-build compile build lint \\
	install-py3-conda install-py3-pyenv install-deps \\
	dist python-dist dist-test docker-dist docker-dist-test \\
	epmt-dash \\
	papiex-dist \\
	epmt-full-release check-release \\
	release \\
	clean-extra clean-all clean distclean dashclean dockerclean papiexclean \\
	check check-epmt-check check-integration-tests check-unittests

# general things? 
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
	pip3 install -r $(EPMT_DASH_SRC)/requirements-ui.txt.py3
#	pip3 install -r src/epmt/ui/requirements-ui.txt.py3

# This target runs pyinstaller, outputs a tarball with
# epmt + all dependencies included
$(EPMT_RELEASE) dist:
	@echo "(EPMT_RELEASE dist) whoami: $(shell whoami)"
	@echo "WARNING removing directories: rm -rf epmt-install build"
	rm -rf epmt-install build && mkdir -p epmt-install/epmt/epmtdocs
	@echo "DONE removing epmt-install/ build/ and recreating epmt-install/epmt/epmt-docs"
#	README
	cp README.md src/README.md && echo "README.md copy went well"
	@echo
	@echo
	@echo "**********************************************************"
	@echo "*************** calling pyinstaller **********************"
	@echo "**********************************************************"
	pyinstaller --version
#	@echo "pyinstaller --clean --noconfirm --distpath=epmt-install epmt.spec"
#	pyinstaller --clean --noconfirm --distpath=epmt-install epmt.spec
	@echo "WARNING NOT CLEAN: pyinstaller --noconfirm --distpath=epmt-install epmt.spec"
	pyinstaller --noconfirm --distpath=epmt-install epmt.spec
	@echo
	@echo
	@echo "**********************************************************"
	@echo "****************** calling mkdocs ************************"
	@echo "**********************************************************"
#   add --dirty to the build call to utilize the cache when building docs
	@echo "WARNING DIRTY: mkdocs build --dirty -f epmtdocs/mkdocs.yml"
	mkdocs build --dirty -f epmtdocs/mkdocs.yml
#	@echo "mkdocs build -f epmtdocs/mkdocs.yml"
#	mkdocs build -f epmtdocs/mkdocs.yml
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

# runs setuptools
# note that this step requires EPMT_RELEASE and PAPIEX_RELEASE, but we don't explicitly state it here, b.c.
# when we go in the docker container, the time-zone changes and therefore thet timestamp comparison triggers re-making
# targets that do not need to be remade
python-dist:
	@echo "(python-dist) whoami: $(shell whoami)"
	@echo "**********************************************************"
	@echo "************** python3 setup.py sdist ********************"
	@echo "**********************************************************"	
	cd src && echo "GOOD: cd src" || echo "I FAILED: cd src"; \
	tar zxf ../$(PAPIEX_RELEASE) && echo "GOOD: tar -zxf ../PAPIEX_RELEASE" || echo "I FAILED: tar zxf ../PAPIEX_RELEASE"; \
	python3 setup.py sdist && echo "GOOD: python3 setup.py sdist" || echo "I FAILED: python3 setup.py sdist"; \
	chmod a+r dist/* && echo "GOOD: chmod a+r dist/*" || echo "I FAILED: chmod a+r dist/*"

# creates a tarball containing test directories. If the test directory exists, clobber and re-create
test-$(EPMT_RELEASE) dist-test:
	@echo "(test-EPMT_RELEASE dist-test) whoami: $(shell whoami)"
	@echo
	@echo "WARNING recreating directories: epmt-install-tests"
	rm -rf epmt-install-tests && mkdir epmt-install-tests
	@echo "DONE recreating directories: rm -rf epmt-install-tests"
	@echo
	cp -Rp src/epmt/test epmt-install-tests
	@echo "creating test-tarball in final location: test-${EPMT_RELEASE}"
	tar -czf test-$(EPMT_RELEASE) epmt-install-tests
	@echo
	@echo "WARNING removing directory to clean up: rm -rf epmt-install-tests"
	rm -rf epmt-install-tests

# this target 1) builds an image with an environment inwhich we'd like to build our applicaiton
# 2) builds that application within a running container of that image
# NOTE: bind mounts to current working directory, usually the repository directory
docker-dist:
	@echo "(docker-dist) whoami: $(shell whoami)"
	@echo " ------ CREATE EPMT TARBALL: docker-dist ------- "
	@echo "       build command = ${DOCKER_BUILD}"
	@echo "       run   command = ${DOCKER_RUN}"
	@echo "       run   options = ${DOCKER_RUN_OPTS}"
	@echo
	@echo
	@echo " - docker build <STUFF> Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build"
	@echo "       we are creating a container environment inwhich to build the python distribution"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build -t $(OS_TARGET)-epmt-build:$(EPMT_VERSION) \
	--build-arg sqlite_version=$(SQLITE_VERSION) \
	--build-arg sqlite_year=$(SQLITE_YEAR) \
	--build-arg python_version=$(PYTHON_VERSION) .
	@echo
	@echo
	@echo " - docker run <STUFF> <use image built from Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build>"
	@echo "       within a running contianer of the image we just built, now build the python application."
	@echo "       i.e. running make dist python-dist dist-test inside $(OS_TARGET)-epmt-build"
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --privileged \
	--volume=$(PWD):$(PWD) \
	-w $(PWD) $(OS_TARGET)-epmt-build:$(EPMT_VERSION) \
	make --debug OS_TARGET=$(OS_TARGET) dist python-dist dist-test
#   wait.... is this one of those ... "pip install it twice deals? commenting out for now..."
#	make --debug OS_TARGET=$(OS_TARGET) dist python-dist $(EPMT_RELEASE) dist-test


# tests distribution within a container
docker-dist-test:
	@echo "(docker-dist-test) whoami: $(shell whoami)"
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --privileged \
	--volume=$(PWD):$(PWD) \
	-w $(PWD) $(OS_TARGET)-epmt-build:$(EPMT_VERSION) \
	make --debug OS_TARGET=$(OS_TARGET) dist-test


# ----------- EPMT_DASH THINGS ---------- #
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
	ln -s ../../$(EPMT_DASH_SRC)/docs/index.md index.md || \
	echo "symbolic link creation failed."; \
	cd -

$(EPMT_DASH_SRC_TARBALL):
	@echo "(EPMT_DASH_SRC_TARBALL) whoami: $(shell whoami)"
	echo "grabbing epmt-dash via curl"; \
	curl -O $(EPMT_DASH_SRC_URL); \
	ls $(EPMT_DASH_SRC_TARBALL); \
# ----------- \end EPMT_DASH THINGS ---------- #


# ----------- PAPIEX THINGS ---------- #
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
	else \
	echo "making docker-dist within PAPIEX_SRC/PAPIEX_RELEASE target"; \
	make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) docker-dist; \
	fi

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
# ----------- \end PAPIEX THINGS ---------- #


# ----------- EPMT_FULL_RELEASE THINGS ---------- #
epmt-full-release: $(EPMT_FULL_RELEASE)
	@echo "(epmt-full-release) whoami: $(shell whoami)"

$(EPMT_FULL_RELEASE): $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE)
	@echo "(EPMT_FULL_RELEASE) whoami: $(shell whoami)"
	@echo "Making EPMT $(EPMT_VERSION) for $(OS_TARGET): $^"
	tar -cvzf $(EPMT_FULL_RELEASE) $(notdir $^)
	@echo
	@echo "$(EPMT_FULL_RELEASE) build complete!"
	@echo

build-check-release: $(EPMT_FULL_RELEASE)
	@echo "(build-check-release) whoami: $(shell whoami)"
	@echo "creating an all-included testing environment / delivery tarball"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test-release \
	-t $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) \
	--build-arg epmt_version=$(EPMT_VERSION) \
	--build-arg install_path=$(EPMT_INSTALL_PATH) \
	--build-arg install_prefix=$(EPMT_INSTALL_PREFIX) \
	--build-arg epmt_full_release=$(EPMT_FULL_RELEASE) \
	--build-arg epmt_python_full_release=$(EPMT_PYTHON_FULL_RELEASE) \
	--build-arg sqlite_version=$(SQLITE_VERSION) \
	--build-arg sqlite_year=$(SQLITE_YEAR) \
	--build-arg python_version=$(PYTHON_VERSION) .
	@echo 

check-release:
	@echo "(check-release) whoami: $(shell whoami)"
	@echo "looking for postgres-test container"
	if docker ps | grep postgres-test > /dev/null; \
	then docker stop postgres-test; fi
	@echo
	@echo "looking for epmt-test-net docker networks"
	if docker network ls | grep epmt-test-net > /dev/null; \
	then docker network rm -f epmt-test-net; fi
	@echo
	@echo
	@echo "creating epmt-test-net docker network"
	docker network create epmt-test-net
	@echo
	@echo "running postgres-test container"
	$(DOCKER_RUN) -d --rm --name postgres-test --network epmt-test-net --privileged \
	-e POSTGRES_USER=postgres \
	-e POSTGRES_PASSWORD=example \
	-e POSTGRES_DB=EPMT-TEST postgres:latest
	@echo
	@echo
	@echo "looking for prev ran epmt-test-release container to remove..."
	if docker container ls -a | grep epmt-$(EPMT_VERSION)-test-release > /dev/null; \
	then docker container rm $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release; sleep 2; fi
	@echo
	@echo "running epmt-test-release container"
	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release \
	--network epmt-test-net \
	--privileged $(DOCKER_RUN_OPTS) \
	-h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) \
	bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; epmt -vv -V; \
	echo ""; \
	echo ""; \
	echo "" && echo "------ epmt -vv check ------" && epmt -vv check \
	|| echo "epmt -vv check failure guard, keep going"; \
	echo ""; \
	echo ""; \
	echo "" && echo "------ epmt -vv unittest ------" && epmt -vv unittest \
	|| echo "epmt -vv unittest failure guard, keep going"; \
	echo ""; \
	echo ""; \
	echo "" && echo "------ epmt integration ------" && epmt integration \
	|| echo "epmt integration failure guard, keep going"; \
	echo ""'
	@echo
	@echo
# ----------- \end EPMT_FULL_RELEASE THINGS ---------- #


# ----------- release targets ---------- #
release:
	@echo "(release) whoami: $(shell whoami)"
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
	@echo
	@echo " ------ MAKE : docker-dist / DIST ------- "
	$(MAKE) docker-dist
	@echo
	@echo
	@echo " ------ MAKE : epmt-full-release / FULL-RELEASE ------- "
	$(MAKE) epmt-full-release
	@echo
	@echo
	@echo " ------ MAKE : build-check-release / CHECK-RELEASE ------- "
	$(MAKE) build-check-release
	@echo
	@echo
	@echo " ------ MAKE : check-release / CHECK-RELEASE ------- "
	$(MAKE) check-release
	@echo
	@echo
	@echo "done building epmt"
# ----------- \end release targets ---------- #


# ----------- CLEANING ---------- #
clean-extra: clean-all papiexclean dashclean
	@echo "(clean-extra) whoami: $(shell whoami)"

clean-all: clean distclean dockerclean 
	@echo "(clean-all) whoami: $(shell whoami)"

clean:
	@echo "(clean) whoami: $(shell whoami)"
	- find . -type f \( -name "core" -or -name "*~" -or -name "*.pyc" -or -name "epmt.log" \) -exec rm -f {} \;
	- rm -rf $(EPMT_DASH_SRC)/__pycache__ __pycache__ build epmt-install epmt-install-tests .venv374

distclean:
	@echo "(distclean) whoami: $(shell whoami)"
	- rm -f settings.py $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(EPMT_FULL_RELEASE) src/dist/*
	- rm -rf epmtdocs/site 

dashclean:
	@echo "(dashclean) whoami: $(shell whoami)"
	- rm -rf $(EPMT_DASH_SRC)
	- rm -f $(EPMT_DASH_SRC_TARBALL)
	- rm -f epmtdocs/docs/index.md

dockerclean:
	@echo "(dockerclean) whoami: $(shell whoami)"
	- docker image rm --force \
	$(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) $(OS_TARGET)-epmt-build:$(EPMT_VERSION)

papiexclean:
	@echo "(papiexclean) whoami: $(shell whoami)"
	- rm -fr $(PAPIEX_SRC) 
	- rm -f $(PAPIEX_SRC_TARBALL) $(PAPIEX_RELEASE)
# ----------- \end CLEANING ---------- #


# ----------- CHECKING/TESTING ---------- #
check: check-epmt-check check-integration-tests check-unittests
	@echo "(check) whoami: $(shell whoami)"

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
#   epmt.test.test_lib epmt.test.test_stat epmt.test.test_settings \
#	epmt.test.test_anysh epmt.test.test_submit epmt.test.test_run \
#	epmt.test.test_cmds epmt.test.test_query epmt.test.test_explore \
#	epmt.test.test_outliers epmt.test.test_db_schema epmt.test.test_db_migration
# ----------- \end CHECKING (not used?) ---------- #
