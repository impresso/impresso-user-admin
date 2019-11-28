build:
	docker build -t impresso/impresso-user-admin .

run:
	docker run \
		-v $(PWD)/.dev.env:/impresso-user-admin/.docker.env \
		-e "ENV=docker" \
		-it impresso/impresso-user-admin \
		python ./manage.py runserver
