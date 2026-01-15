# impresso-user-admin

A basic django application to manage user-related information contained in [Impresso's Master DB](https://github.com/impresso/impresso-master-db).
We use `pipenv` for development together with `docker`. Please look at the relevant sections in the documentation.

## Development

Take the time to explore the `.example.env` file and the related `./impresso/settings.py` to understand the settings that can be configured via environment variables for your specific environment. We have configured `dotenv` in `./impresso/base.py` to allow the loading of different `.env` files. For example, you can use `.env` or `.dev.env` for development, and `.prod.env` to test production settings.

```sh
# our .dev.env file, that connects to the local redis instance
REDIS_HOST=localhost:6379
IMPRESSO_DB_HOST=localhost
IMPRESSO_DB_PORT=3306
# Then don't forget to fill all SOLR related settings accordiung to your impresso configuration
IMPRESSO_SOLR_URL=http://localhost:8983/solr/impresso
IMPRESSO_SOLR_USER=your-user-reader-only
IMPRESSO_SOLR_PASSWORD=our-user-reader-only-password
IMPRESSO_SOLR_USER_WRITE=your-user-write-allowed
IMPRESSO_SOLR_PASSWORD_WRITE=your-user-write-allowed-password
IMPRESSO_SOLR_PASSAGES_URL=http://localhost:8983/solr/impresso-tr-passages
```

To start the Django admin, you need to have Redis and MySQL running. You can start them by running the command `docker compose up`. Please note that in our YAML file, the ports for Redis and MySQL are exposed to facilitate local development and testing.

```sh
docker compose up -d --env-file=.dev.env
```

Then you can start the development server, e.g. with pipenv and the `dev.env` file:

```sh
ENV=dev pipenv run ./manage.py runserver
```

or with Makefile:

```sh
ENV=dev make run-dev
```

To start _celery_ task manager in development with pipenv, in a new terminal:

```sh
ENV=dev pipenv run celery -A impresso worker -l info
```

Of course, you can also use a generic `.env file` on development, in this case you don't need to specify the `ENV` variable:

```sh
docker compose up -d
pipenv run ./manage.py runserver
# and in another terminal, to start the celery worker
pipenv run celery -A impresso worker -l info
```

Finally, use mypy to check for type errors:

```sh
pipenv run mypy --config-file ./.mypy.ini impresso
```

### setup with pyenv + pipenv

Follow the instruction to install [pyenv](https://github.com/pyenv/pyenv), motivation on this choice can be found on [hackernoon "Why you should use pyenv + Pipenv for your Python projects"](https://hackernoon.com/reaching-python-development-nirvana-bb5692adf30c)
and more details on pyenv on [Managing Multiple Python Versions with pyenv](http://akbaribrahim.com/managing-multiple-python-versions-with-pyenv/)

```sh
eval "$(pyenv init -)"
cd /path/to/impresso-user-admin/
pyenv version
```

The last command gives you the version of the local python. If it doesn't meet the version number specified in Pipfile,
use pyenv install command:

```sh
pyenv install 3.12.4
```

Use pip to install Pipenv:

```sh
python -m pip install pipenv
```

Then run

```sh
pipenv --python 3.12 install
```

To create and activate the virtualenv. Once in the shell, you can go back with the `exit` command and reactivate the virtualenv simply `pipenv shell`

## configure: setup dotenv files

Django settings.py is enriched via `dotenv` files, special and simple configuration files.
We use a dotenv file to store sensitive settings and to store settings for a specific environment ("development" or "production"). A dotenv file is parsed when we set its prefix in the `ENV` environment variable, that is, `.dev.env` is used when we have `ENV=dev`:

```sh
ENV=dev pipenv run ./manage.py runserver
```

This command runs the development server enriching the settings file with the cofiguration stored in the `.dev.env` file.
Please use the `.example.env` file as astarting point to generate specific environment configuration (e.g. `prod` or `sandbox`).

If needed (that is for local development), run:

```
ENV=dev pipenv run ./manage.py migrate
```

### Useful commands

Create a new admin user in the database

```sh
ENV=dev pipenv run ./manage.py createsuperuser
```

Create multiple users at once, with randomly generated password.

```sh
ENV=dev pipenv run ./manage.py createaccount guestA@uni.lu guestB@uni.lu
```

Stop a specific job from command line:

```sh
ENV=dev pipenv run python ./manage.py stopjob 1234
```

## Running tests

Specify the environment variable `ENV=test` to run the tests with the `console` email backend:

```sh
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend ENV=test pipenv run ./manage.py test
```

## Use in production

Please check the included Dockerfile to generate your own docker image or use the docker image available on impresso dockerhub.

Test image locally:

```
make run
```

### Using a proxy

If the database is only accessible via a socks proxy, add the following to your `.env` file:

```bash
IMPRESSO_SOCKS_PROXY_CONFIG='{ "host": "localhost", "port": 1080, "domains": ["db.domain.com"] }'
```

## Project

The 'impresso - Media Monitoring of the Past' project is funded by the Swiss National Science Foundation (SNSF) under grant number [CRSII5_173719](http://p3.snf.ch/project-173719) (Sinergia program). The project aims at developing tools to process and explore large-scale collections of historical newspapers, and at studying the impact of this new tooling on historical research practices. More information at https://impresso-project.ch.

## License

Copyright (C) 2020 The _impresso_ team. Contributors to this program include: [Daniele Guido](https://github.com/danieleguido), [Roman Kalyakin](https://github.com/theorm).
This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but without any warranty; without even the implied warranty of merchantability or fitness for a particular purpose. See the [GNU Affero General Public License](https://github.com/impresso/impresso-user-admin/blob/master/LICENSE) for more details.
