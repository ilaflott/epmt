VERSION=2.0.0
RELEASE=epmt-$(VERSION).tgz
SHELL=/bin/bash
PWD=$(shell pwd)

.PHONY: default build \\
	epmt-build epmt-test \\
	clean distclean \\
	check check-python-native check-python-driver check-python-2.6 check-python-2.7 check-python-3

build:
	python -bb -m py_compile *.py orm/*.py orm/*/*.py test/*.py

dist:
	rm -rf epmt-install
	pyinstaller --hidden-import sqlalchemy.ext.baked --exclude-module settings --clean --distpath=epmt-install -s epmt
	cp -Rp preset_settings epmt-install
#	--hidden-import epmt_default_settings --exclude-module settings 
	rm -f $(RELEASE); tar cvfz $(RELEASE) epmt-install
	rm -rf epmt-install build epmt.spec

dist-test:
	rm -rf epmt-install-tests
	mkdir epmt-install-tests
	cp -Rp test Makefile epmt-example.csh epmt-example.sh epmt-install-tests
	rm -f test-$(RELEASE); tar cvfz test-$(RELEASE) epmt-install-tests
	rm -rf epmt-install-tests

$(RELEASE) test-$(RELEASE) docker-dist: 
	docker build -f Dockerfiles/Dockerfile.centos-7-epmt-build -t centos-7-epmt-build .
	docker run -i --tty --rm --volume=$(PWD):$(PWD):z -w $(PWD) centos-7-epmt-build make distclean dist dist-test

docker-test-dist: $(RELEASE) test-$(RELEASE)
	docker build -f Dockerfiles/Dockerfile.centos-7-epmt-test -t centos-7-epmt-test --build-arg release=$(VERSION) .
	docker run --privileged --rm -it centos-7-epmt-test

docker-dist-slurm:
	docker build -f Dockerfiles/Dockerfile.slurm-centos-7 -t centos7-epmt-papiex-slurm-test --build-arg release=$(VERSION) .

docker-test-dist-slurm: docker-dist-slurm
	docker run --name centos7-slurm --privileged -dt --rm --volume=$(PWD):$(PWD):z -w $(PWD) -h ernie centos7-epmt-papiex-slurm-test tail -f /dev/null
	docker exec centos7-slurm epmt check
	docker exec centos7-slurm srun -n1 /opt/epmt/examples/epmt-example.sh
	docker exec centos7-slurm srun -n1 /opt/epmt/examples/epmt-example.csh
	docker exec centos7-slurm srun -n1 --task-prolog=/opt/epmt/slurm/slurm_task_prolog_epmt.sh --task-epilog=/opt/epmt/slurm/slurm_task_epilog_epmt.sh hostname
	docker exec centos7-slurm srun -n1 --task-prolog=/opt/epmt/slurm/slurm_task_prolog_epmt.sh --task-epilog=/opt/epmt/slurm/slurm_task_epilog_epmt.sh sleep 1
	ls 2.tgz 3.tgz 4.tgz 5.tgz
	docker exec centos7-slurm epmt submit 2.tgz 3.tgz 4.tgz 5.tgz
	docker exec centos7-slurm sed -i '$$s;$$;\nTaskProlog=/opt/epmt/slurm/slurm_task_prolog_epmt.sh\n;' /etc/slurm/slurm.conf
	docker exec centos7-slurm sed -i '$$s;$$;\nTaskEpilog=/opt/epmt/slurm/slurm_task_epilog_epmt.sh\n;' /etc/slurm/slurm.conf
	docker exec centos7-slurm killall -s SIGHUP slurmctld slurmd
	docker exec centos7-slurm srun -n1 hostname
	docker exec centos7-slurm srun -n1 sleep 1
	ls 6.tgz 7.tgz
	docker exec centos7-slurm epmt submit 6.tgz 7.tgz
	docker stop centos7-slurm

clean:
	find . -name "*~" -o -name "*.pyc" -exec rm -f {} \; 
	rm -rf __pycache__
distclean: clean
	rm -f settings.py test-$(RELEASE) $(RELEASE)
	rm -rf epmt-install epmt-install-tests build epmt.spec
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
	python3 -V
	@env -i PATH=${PWD}:${PATH} python3 -m unittest -v -f test.test_lib test.test_settings test.test_anysh test.test_submit test.test_misc test.test_query test.test_outliers test.test_db_schema
