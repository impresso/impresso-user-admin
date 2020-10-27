# impresso-user-admin

A basic django application to manage user-related information contained in [Impresso's Master DB](https://github.com/impresso/impresso-master-db).
We use `pipenv`for development and `docker` for production. Please look at the relevant sections in the documentation.

To start *django admin* in development with pipenv:

    ENV=dev pipenv run ./manage.py runserver

To start *celery* task manager in development with pipenv:

    ENV=dev pipenv run celery -A impresso worker -l info


### setup with pyenv + pipenv
Follow the instruction to install [pyenv](https://github.com/pyenv/pyenv), motivation on this choice can be found on [hackernoon "Why you should use pyenv + Pipenv for your Python projects"](https://hackernoon.com/reaching-python-development-nirvana-bb5692adf30c)
and more details on pyenv on [Managing Multiple Python Versions with pyenv](http://akbaribrahim.com/managing-multiple-python-versions-with-pyenv/)

```
eval "$(pyenv init -)"
cd /path/to/impresso-user-admin/
pyenv version
```
The last command gives you the version of the local python. If it doesn't meet the version number specified in Pipfile,
use pyenv install command:
```
pyenv install 3.6.9
```
Use pip to install Pipenv:
```
python -m pip install pipenv
```
Then run
```
pipenv --python 3.6.9 install
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

Index a collection stored in the db using its <id>:
```sh
ENV=dev ./manage.py synccollection test-abcd
```

Export query as csv using (first argument being `user_id` then the solr query):
```sh
ENV=dev ./manage.py exportqueryascsv 1 "content_txt_fr:\"premier ministre portugais\""
```

## Use in production
Please check the included Dockerfile to generate your own docker image or use the docker image available on impresso dockerhub.

Test image locally:
```
make run
```

                       
## Project
The 'impresso - Media Monitoring of the Past' project is funded by the Swiss National Science Foundation (SNSF) under  grant number [CRSII5_173719](http://p3.snf.ch/project-173719) (Sinergia program). The project aims at developing tools to process and explore large-scale collections of historical newspapers, and at studying the impact of this new tooling on historical research practices. More information at https://impresso-project.ch.
## License
Copyright (C) 2020  The *impresso* team. Contributors to this program include: [Daniele Guido](https://github.com/danieleguido), [Roman Kalyakin](https://github.com/theorm).
This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. 
This program is distributed in the hope that it will be useful, but without any warranty; without even the implied warranty of merchantability or fitness for a particular purpose. See the [GNU Affero General Public License](https://github.com/impresso/impresso-user-admin/blob/master/LICENSE) for more details.
