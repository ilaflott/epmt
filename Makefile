.ONESHELL:

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
#DOCKER_RUN_OPTS:=--rm -it
DOCKER_RUN_OPTS:= -it
#DOCKER_BUILD:=docker -D build --no-cache -f
DOCKER_BUILD:=docker -D build -f
PWD=$(shell pwd)

#### ---- # this prints which target is being run. from percipio learning
##SHELL += -x
OLD_SHELL := $(SHELL)
SHELL = $(warning ------- TARGET is -- $@ -- )$(OLD_SHELL)


#.PHONY: default \\
#	epmt-build epmt-test \\
#	clean distclean \\
#	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3 check-integration-tests\\
#	dist build compile lint release release6 release7 release-all \\
#	install-py3-pyenv install-py3deps-pyenv

#epmt-build compile build:
#	@echo "whoami: $(shell whoami)"
#	cd src/epmt
#	python3 -O -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py

#lint:
#	@echo "whoami: $(shell whoami)"
#	cd src/epmt
#	python3 -m pylint -E *.py orm/*.py orm/*/*.py test/*.py


## install a virtual environment
#install-py3-conda:
#	@echo "whoami: $(shell whoami)"
#	set -e; echo "Installing Python $(PYTHON_VERSION) using conda" ; \
#	conda create -n $(EPMT_VERSION)_py$(PYTHON_VERSION) python=$(PYTHON_VERSION) -y ; \
#	$(CONDA_ACTIVATE) $(EPMT_VERSION)_py$(PYTHON_VERSION) ; $(MAKE) install-deps ; \
#	echo ; echo "Your virtual python environment is epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION)." ;

#install-py3-pyenv:
#	@echo "whoami: $(shell whoami)"
#	set -e; echo "Installing Python $(PYTHON_VERSION) using pyenv"  
#	PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install -s $(PYTHON_VERSION)  ; \
#	pyenv virtualenv $(PYTHON_VERSION) epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION) ; \
#	pyenv local epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION) ; $(MAKE) install-deps ; \
#	echo ; echo "Your virtual python environment is epmt-$(EPMT_VERSION)_py$(PYTHON_VERSION)." ;

#install-deps:
#	@echo "whoami: $(shell whoami)"
#	set -e ; pip install --upgrade pip ; pip install -r requirements.txt.py3 ; pip install -r src/epmt/ui/requirements-ui.txt.py3

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
	@echo "whoami: $(shell whoami)"
	@echo " - running pyinstaller and building epmt docs, etc. also some cleaning and moving things around."
	rm -rf epmt-install build
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


python-dist: $(EPMT_RELEASE) 
	@echo "whoami: $(shell whoami)"
	@echo " - in container, extracting papiex_release and running setuptools"
	cd src
	tar zxf ../$(PAPIEX_RELEASE)
	python3 setup.py sdist
	chmod a+r dist/*

test-$(EPMT_RELEASE) dist-test:
	@echo "whoami: $(shell whoami)"
	@echo " - putting installation tests in the right place"
# final location of tarfile
	rm -rf epmt-install-tests && mkdir epmt-install-tests
	cp -Rp src/epmt/test epmt-install-tests
	tar -czf test-$(EPMT_RELEASE) epmt-install-tests
	rm -rf epmt-install-tests

docker-dist: $(PAPIEX_RELEASE)
	@echo "whoami: $(shell whoami)"
	@echo " - building epmt and epmt-test tarball via Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build -t $(OS_TARGET)-epmt-build --build-arg python_version=$(PYTHON_VERSION) .
	@echo " - running make python-dist dist-test inside container created from image (Dockerfile.$(OS_TARGET)-epmt-build)"
#	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) python-dist $(EPMT_RELEASE) dist-test
#	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) python-dist dist dist-test
	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) dist python-dist dist-test

#docker-dist-test:
#	@echo "whoami: $(shell whoami)"
##	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) -it --rm --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) dist-test
#	$(DOCKER_RUN) $(DOCKER_RUN_OPTS) -it --volume=$(PWD):$(PWD) -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) dist-test

papiex-dist: $(PAPIEX_RELEASE)
	@echo "whoami: $(shell whoami)"
	@echo " - gonna compile papiex, going to make target $(PAPIEX_RELEASE)"

$(PAPIEX_RELEASE): $(PAPIEX_SRC)/$(PAPIEX_RELEASE)
	@echo " - gonna compile papiex, going to make target $(PAPIEX_SRC)/$(PAPIEX_RELEASE)"
	@echo "whoami: $(shell whoami)"
	cp $< $@

$(PAPIEX_SRC)/$(PAPIEX_RELEASE):
	@echo "whoami: $(shell whoami)"
	make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) docker-dist 

epmt-full-release: $(EPMT_FULL_RELEASE)
	@echo "whoami: $(shell whoami)"

$(EPMT_FULL_RELEASE): $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(PAPIEX_RELEASE)
	@echo "whoami: $(shell whoami)"
	@echo "Making EPMT $(EPMT_VERSION) for $(OS_TARGET): $^"
	tar -cvzf $(EPMT_FULL_RELEASE) $(notdir $^)
	@echo
	@echo "$(EPMT_FULL_RELEASE) build complete!"
	@echo

check-release release-test-docker: $(EPMT_FULL_RELEASE)
	@echo "whoami: $(shell whoami)"
	$(DOCKER_BUILD) Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test-release -t $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) --progress plain --build-arg epmt_version=$(EPMT_VERSION) --build-arg install_path=/opt/minimalmetrics --build-arg epmt_full_release=$(EPMT_FULL_RELEASE) --build-arg epmt_python_full_release=$(EPMT_PYTHON_FULL_RELEASE)  .
#	if docker ps | grep postgres-test > /dev/null; then docker stop postgres-test; fi
#	if docker network ls | grep epmt-test-net > /dev/null; then docker network rm epmt-test-net; fi
#	docker network create epmt-test-net
##	$(DOCKER_RUN) -d --rm --name postgres-test --network epmt-test-net -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT-TEST postgres:latest
#	$(DOCKER_RUN) -d --name postgres-test --network epmt-test-net -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT-TEST postgres:latest
##	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net --privileged -it --rm -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:`; cp -fv $$install_prefix/preset_settings/settings_test_pg_container.py $$install_prefix/settings.py && epmt check && epmt unittest && epmt integration'
#	$(DOCKER_RUN) --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --network epmt-test-net --privileged -it -h slurmctl $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid; install_prefix=`epmt -h| grep install_prefix|cut -f2 -d:`; cp -fv $$install_prefix/preset_settings/settings_test_pg_container.py $$install_prefix/settings.py && epmt check && epmt unittest && epmt integration'
#	docker stop postgres-test
#	docker network rm epmt-test-net

release release-all release7:
	@echo "whoami: $(shell whoami)"
	@echo " - building everything!"

###      # this step is fine- just cleaning.
##	$(MAKE) clean distclean docker-clean papiex-clean

##      # make the papiex tarball, this is now here because prev. the targets didn't really reflect the dependency on papiex
#	$(MAKE) papiex-dist

##	# this step is good it seems, docker-dist --> <stuff> ... docker run <blah> make <container targs>
##      # where <container targs> = python-dist dist dist-test
#	$(MAKE) docker-dist

##	# this should just make a tar ball. nothing else. this step seems fine with the papiex step above.
#	$(MAKE) epmt-full-release

#	# moment of truth. 
	$(MAKE) check-release

clean:
	@echo "whoami: $(shell whoami)"
	@echo " - cleaning up __pycache__ amongst other things."
	find . -type f \( -name "core" -or -name "*~" -or -name "*.pyc" -or -name "epmt.log" \) -exec rm -f {} \;
	rm -rf src/epmt/ui/__pycache__ __pycache__ build epmt-install epmt-install-tests .venv374ß

distclean: 
	@echo "whoami: $(shell whoami)"
	@echo " - cleaning up tarballs, python-related things, epmtdocs"
	rm -f settings.py $(EPMT_RELEASE) test-$(EPMT_RELEASE) $(EPMT_FULL_RELEASE) src/dist/*
	rm -rf epmtdocs/site

papiex-clean:
	@echo "whoami: $(shell whoami)"
	@echo " - cleaning up papiex"
	rm -f $(PAPIEX_SRC)/$(PAPIEX-RELEASE)

docker-clean:
	@echo "whoami: $(shell whoami)"
	@echo " - cleaning up docker images"
	- docker image rm --force $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) $(OS_TARGET)-epmt-build




## Simple python version testing with no database
##
#
## We should get rid of this in favor of a sequence of epmt commands.
#
#check: check-unittests check-integration-tests
#	@echo "whoami: $(shell whoami)"
#
#check-unittests: # Why not test all of them?
#	@echo "whoami: $(shell whoami)"
#	@env -i TERM=ansi PATH=${PWD}:${PATH} epmt unittest
##@env -i TERM=ansi PATH=${PWD}:${PATH} python3 -m unittest -v -f test.test_lib test.test_stat test.test_settings test.test_anysh test.test_submit test.test_run test.test_cmds test.test_query test.test_explore test.test_outliers test.test_db_schema test.test_db_migration
#check-integration-tests:
#	@echo "whoami: $(shell whoami)"
#	@env -i TERM=ansi PATH=${PWD}:${PATH} epmt integration
