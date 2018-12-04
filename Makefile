.PHONY: docker-build docker-test default
default: docker-build docker-test
docker-build:
	docker build . -t epmt
docker-test:
	docker run epmt
