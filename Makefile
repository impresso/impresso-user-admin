BUILD_TAG ?= latest

build:
	docker build \
	-t impresso/impresso-user-admin${BUILD_TAG} \
	--build-arg GIT_TAG=$(shell git describe --tags) \
	--build-arg GIT_BRANCH=$(shell git rev-parse --abbrev-ref HEAD) \
	--build-arg GIT_REVISION=$(shell git rev-parse --short HEAD) .

run:
	docker run \
		-v $(PWD)/.dev.env:/impresso-user-admin/.docker.env \
		-e "ENV=docker" \
		-it impresso/impresso-user-admin \
		python ./manage.py runserver

run-dev:
	IMPRESSO_GIT_TAG=${BUILD_TAG} \
	IMPRESSO_GIT_BRANCH=$(shell git rev-parse --abbrev-ref HEAD) \
	IMPRESSO_GIT_REVISION=$(shell git rev-parse --short HEAD) \
	pipenv run ./manage.py runserver 8888
