OS_TARGET=centos-6
VERSION=$(shell python3 -m epmtlib)
RELEASE=epmt-$(VERSION).tgz
EPMT_RELEASE = EPMT-release-$(VERSION)-$(OS_TARGET).tgz
SHELL=/bin/bash
PWD=$(shell pwd)

.PHONY: default \\
	epmt-build epmt-test \\
	clean distclean \\
	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3 check-integration-tests \\
	dist build release release6 release7 release-all

build:
	python -O -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py

dist: 
	rm -rf epmt-install
	pyinstaller --clean --distpath=epmt-install epmt.spec
	cp -Rp preset_settings epmt-install
	cp -Rp notebooks epmt-install
	mkdir epmt-install/examples
	cp epmt-example.sh epmt-example.csh epmt-install/examples
	mkdir epmt-install/slurm
	cp SLURM/slurm_task_*log_epmt.sh epmt-install/slurm
	rm -f $(RELEASE); tar cvfz $(RELEASE) epmt-install
	rm -rf epmt-install build

dist-test:
	rm -rf epmt-install-tests
	mkdir epmt-install-tests
	cp -Rp test Makefile epmt-example.csh epmt-example.sh epmt-install-tests
	rm -f test-$(RELEASE); tar cvfz test-$(RELEASE) epmt-install-tests
	rm -rf epmt-install-tests

docker-dist $(RELEASE) test-$(RELEASE): 
	docker build -f Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-build -t $(OS_TARGET)-epmt-build .
	docker run -i --tty --rm --volume=$(PWD):$(PWD):z -w $(PWD) $(OS_TARGET)-epmt-build make distclean dist dist-test

docker-test-dist: $(RELEASE) test-$(RELEASE)
	docker build -f Dockerfiles/Dockerfile.$(OS_TARGET)-epmt-test -t $(OS_TARGET)-epmt-test --build-arg release=$(VERSION) .
	docker run --rm -it $(OS_TARGET)-epmt-test

docker-dist-slurm: $(RELEASE)
	docker build -f Dockerfiles/Dockerfile.slurm-$(OS_TARGET) -t $(OS_TARGET)-epmt-papiex-slurm-test --build-arg release=$(VERSION) .

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


release6:
	$(MAKE) OS_TARGET=centos-6 release

release7:
	$(MAKE) OS_TARGET=centos-7 release

release:  
	@if [ -f $(EPMT_RELEASE) ]; then echo "$(EPMT_RELEASE) already exists. Please remove it and try again"; exit 1; fi
	@echo "Making EPMT release $(VERSION) for $(OS_TARGET)..."
	@echo " - building epmt and epmt-test tarball.."
	@$(MAKE) docker-dist > /dev/null
	@ls epmt-$(VERSION).tgz test-epmt-$(VERSION).tgz
	@echo " - building papiex tarball"
	cd ../papiex-oss; rm -f papiex-epmt-*.tgz;  make OS_TARGET=$(OS_TARGET) docker-dist > /dev/null; cp -v papiex-epmt-*.tgz ../epmt/papiex-epmt-$(VERSION).tgz
	@ls papiex-epmt-$(VERSION).tgz
	@echo "Assembling release tarball"
	tar -czf $(EPMT_RELEASE) epmt-$(VERSION).tgz test-epmt-$(VERSION).tgz papiex-epmt-$(VERSION).tgz
	@echo "Release prepared: $(EPMT_RELEASE)"

release-all:
	$(MAKE) release6 && utils/check-release
	$(MAKE) release7 && utils/check-release

clean:
	find . -name "*~" -o -name "*.pyc" -o -name epmt.log -o -name core -exec rm -f {} \; 
	rm -rf __pycache__
distclean: clean
	rm -f settings.py test-$(RELEASE) $(RELEASE)
	rm -rf epmt-install epmt-install-tests build
# 
# Simple python version testing with no database
#
check: check-python-shells check-unittests check-integration-tests

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
	python3 -V
	@env -i PATH=${PWD}:${PATH} python3 -m unittest -v -f test.test_lib test.test_stat test.test_settings test.test_anysh test.test_submit test.test_cmds test.test_query test.test_explore test.test_outliers test.test_db_schema test.test_db_migration

check-integration-tests:
	test/integration/run_integration
