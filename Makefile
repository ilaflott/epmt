.PHONY: epmt-build epmt-test default clean distclean
default: epmt-build epmt-test
epmt-build:
	docker build . -t epmt:latest
	docker-compose build
epmt-test:
	docker run epmt:latest
	docker-compose up
clean distclean:
	rm -f *~ *.pyc