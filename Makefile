OS_TARGET=centos-6
PAPIEX_VERSION?=2.2.4
PAPIEX_SRC?=../papiex-oss
EPMT_VERSION=$(shell python3 -m epmtlib)
EPMT_RELEASE=epmt-$(EPMT_VERSION)-$(OS_TARGET).tgz
EPMT_FULL_RELEASE=EPMT-release-$(EPMT_VERSION)-$(OS_TARGET).tgz
PAPIEX_RELEASE=papiex-epmt-$(PAPIEX_VERSION)-$(OS_TARGET).tgz
#
SHELL=/bin/bash
PWD=$(shell pwd)

.PHONY: default \\
	epmt-build epmt-test \\
	clean distclean \\
	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3 check-integration-tests\\
	dist build release release6 release7 release-all

build:
	python -O -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py

dist: 
	rm -rf epmt-install build
	pyinstaller --clean --distpath=epmt-install epmt.spec
# resources
	cp -Rp preset_settings epmt-install
	cp -Rp notebooks epmt-install
	cp -Rp migrations epmt-install
	cp -p alembic.ini epmt-install
# examples
	mkdir epmt-install/examples
	cp epmt-example.*sh epmt-install/examples
# slurm
	mkdir epmt-install/slurm
	cp SLURM/slurm_task_*log_epmt.sh epmt-install/slurm
# docs (allowed to fail)
	mkdir -p epmt-install/epmt/epmtdocs
	-mkdocs build -f epmtdocs/mkdocs.yml && cp -Rp epmtdocs/site epmt-install/epmt/epmtdocs
# release
	-@mkdir release 2>/dev/null
	tar -czf release/$(EPMT_RELEASE) epmt-install
	rm -rf epmt-install build

dist-test:
	rm -rf epmt-install-tests
	mkdir epmt-install-tests
	cp -Rp test epmt-install-tests
	-@mkdir release 2>/dev/null
	tar -czf release/test-$(EPMT_RELEASE) epmt-install-tests
	rm -rf epmt-install-tests

docker-dist release/$(EPMT_RELEASE): 
	@echo " - building epmt and epmt-test tarball"
	docker build -f Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build -t $(OS_TARGET)-epmt-build .
	docker run -it --rm --volume=$(PWD):$(PWD):z -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) distclean dist dist-test

docker-dist-test release/test-$(EPMT_RELEASE):
	docker run -it --rm --volume=$(PWD):$(PWD):z -w $(PWD) $(OS_TARGET)-epmt-build make OS_TARGET=$(OS_TARGET) dist-test

papiex-dist release/$(PAPIEX_RELEASE):
	@echo " - building papiex tarball"
	if [ ! -f $(PAPIEX_SRC)/$(PAPIEX_RELEASE) ]; then make -C $(PAPIEX_SRC) OS_TARGET=$(OS_TARGET) docker-dist > /dev/null; fi
	cp $(PAPIEX_SRC)/$(PAPIEX_RELEASE) $(PWD)/release

release epmt-full-release release/$(EPMT_FULL_RELEASE): release/$(EPMT_RELEASE) release/test-$(EPMT_RELEASE) release/$(PAPIEX_RELEASE)
	@echo "Making EPMT $(EPMT_VERSION) for $(OS_TARGET): $^"
	cd release; tar -czf $(EPMT_FULL_RELEASE) $(notdir $^)
	echo "release/$(EPMT_FULL_RELEASE)"

check-release release-test-docker: release/$(EPMT_FULL_RELEASE)
	docker build -f Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test-release -t $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) --build-arg epmt_version=$(EPMT_VERSION) --build-arg install_path=/opt/minimalmetrics --build-arg epmt_full_release=release/$(EPMT_FULL_RELEASE) .
	docker run --name $(OS_TARGET)-epmt-$(EPMT_VERSION)-test-release --privileged -it --rm -h ernie $(OS_TARGET)-epmt-test-release:$(EPMT_VERSION) bash -c "epmt check; epmt unittest; epmt integration"

release6:
# Force rebuild
	rm -f release/$(EPMT_RELEASE) release/test-$(EPMT_RELEASE) release/$(PAPIEX_RELEASE) $(PAPIEX_SRC)/$(PAPIEX_RELEASE)
	$(MAKE) OS_TARGET=centos-6 release check-release

release7:
# Force rebuild
	rm -f release/$(EPMT_RELEASE) release/test-$(EPMT_RELEASE) release/$(PAPIEX_RELEASE) $(PAPIEX_SRC)/$(PAPIEX_RELEASE)
	$(MAKE) OS_TARGET=centos-7 release check-release

release-all: release6 release7

#
#
#
clean:
	find . -type f \( -name "core" -or -name "*~" -or -name "*.pyc" -or -name "epmt.log" \) -exec rm -f {} \;
	rm -rf __pycache__ build epmt-install epmt-install-tests

distclean: clean
	rm -f settings.py release/*$(OS_TARGET)*
	rm -rf epmtdocs/site

# 
# Simple python version testing with no database
#

# We should get rid of this in favor of a sequence of epmt commands.

check: check-python-shells check-unittests check-integration-tests

EPMT_TEST_ENV=PATH=${PWD}:${PATH} SLURM_JOB_USER=`whoami`

check-python-shells:
	@rm -rf /tmp/epmt
	@echo "epmt-example.tcsh (tcsh)" ; env -i SLURM_JOB_ID=111 ${EPMT_TEST_ENV} /bin/tcsh -e epmt-example.tcsh
	@rm -rf /tmp/epmt
	@echo "epmt-example.csh (csh)" ; env -i SLURM_JOB_ID=111 ${EPMT_TEST_ENV} /bin/csh -e epmt-example.csh
	@rm -rf /tmp/epmt
	@echo "epmt-example.bash (bash)" ; env -i SLURM_JOB_ID=222 ${EPMT_TEST_ENV} /bin/bash -Eeu epmt-example.bash
	@rm -rf /tmp/epmt
	@echo "epmt-example.sh (sh)" ; env -i SLURM_JOB_ID=111 ${EPMT_TEST_ENV} /bin/sh -e epmt-example.sh
	@rm -rf /tmp/epmt
check-unittests: # Why not test all of them?
	@env -i TERM=ansi PATH=${PWD}:${PATH} python3 -m unittest -v -f test.test_lib test.test_stat test.test_settings test.test_anysh test.test_submit test.test_run test.test_cmds test.test_query test.test_explore test.test_outliers test.test_db_schema test.test_db_migration
check-integration-tests:
	# Slurm excluded
	@env -i TERM=ansi PATH=${PWD}:${PATH} epmt integration -e -x slurm

#
# Not used
#

docker-test-dist: release/$(EPMT_RELEASE) release/test-$(EPMT_RELEASE)
	docker build -f Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test -t $(OS_TARGET)-epmt-test --build-arg release=release/$(EPMT_RELEASE) --build-arg release_test=release/$(EPMT_RELEASE) .
	docker run --rm -it $(OS_TARGET)-epmt-test

docker-dist-slurm: $(EPMT_RELEASE)
	docker build -f Dockerfiles/Dockerfile.slurm-$(OS_TARGET) -t $(OS_TARGET)-epmt-papiex-slurm-test --build-arg release=$(EPMT_VERSION) .

slurm-start: docker-dist-slurm
	docker run --name $(OS_TARGET)-slurm --privileged -dt --rm --volume=$(PWD):$(PWD):z -w $(PWD) -h ernie $(OS_TARGET)-epmt-papiex-slurm-test tail -f /dev/null

slurm-stop:
	docker stop $(OS_TARGET)-slurm

docker-test-dist-slurm: slurm-start
	docker exec $(OS_TARGET)-slurm epmt check
	docker exec $(OS_TARGET)-slurm srun -n1 /opt/epmt/epmt-install/examples/epmt-example.sh
	docker exec $(OS_TARGET)-slurm srun -n1 /opt/epmt/epmt-install/examples/epmt-example.csh
	docker exec $(OS_TARGET)-slurm srun -n1 --task-prolog=/opt/epmt/epmt-install/slurm/slurm_task_prolog_epmt.sh --task-epilog=/opt/epmt/epmt-install/slurm/slurm_task_epilog_epmt.sh hostname
	docker exec $(OS_TARGET)-slurm srun -n1 --task-prolog=/opt/epmt/epmt-install/slurm/slurm_task_prolog_epmt.sh --task-epilog=/opt/epmt/epmt-install/slurm/slurm_task_epilog_epmt.sh sleep 1
	ls 2.tgz 3.tgz 4.tgz 5.tgz
	docker exec $(OS_TARGET)-slurm epmt submit 2.tgz 3.tgz 4.tgz 5.tgz
	docker exec $(OS_TARGET)-slurm sed -i '$$s;$$;\nTaskProlog=/opt/epmt/epmt-install/slurm/slurm_task_prolog_epmt.sh\n;' /etc/slurm/slurm.conf
	docker exec $(OS_TARGET)-slurm sed -i '$$s;$$;\nTaskEpilog=/opt/epmt/epmt-install/slurm/slurm_task_epilog_epmt.sh\n;' /etc/slurm/slurm.conf
	docker exec $(OS_TARGET)-slurm killall -s SIGHUP slurmctld slurmd
	docker exec $(OS_TARGET)-slurm srun -n1 hostname
	docker exec $(OS_TARGET)-slurm srun -n1 sleep 1
	ls 6.tgz 7.tgz
	docker exec $(OS_TARGET)-slurm epmt submit 6.tgz 7.tgz
	docker stop $(OS_TARGET)-slurm

FORCE:
