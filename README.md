# impresso-user-admin

A basic django application to manage user-related information contained in [Impresso's Master DB](https://github.com/impresso/impresso-master-db).
We use `pipenv`for development and `docker` for production. Please look at the relevant sections in the documentation.

To start _django admin_ in development with pipenv:

    ENV=dev pipenv run ./manage.py runserver

or to test tags:

    ENV=dev make run-dev

To start _celery_ task manager in development with pipenv:

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

Create multiple users at once, with randomly generated password.

```sh
ENV=dev pipenv run ./manage.py createaccount guestA@uni.lu guestB@uni.lu
```

Index a collection stored in the db using its <id>:

```sh
ENV=dev ./manage.py synccollection test-abcd
```

Export query as csv using (first argument being `user_id` then the solr query):

```sh
ENV=dev ./manage.py exportqueryascsv 1 "content_txt_fr:\"premier ministre portugais\""
```

Create (or get) a collection:

```sh
ENV=dev pipenv run ./manage.py createcollection "name of the collection" my-username
```

Then once you get the collection id, usually a concatenation of the creator profile uid and of the slugified version of the desired name, you can add query results to the collection:

```sh
ENV=dev pipenv run python ./manage.py addtocollectionfromquery local-user_name-of-the-collection "content_txt_fr:\"premier ministre portugais\""
```

Index a collection from a list of tr-passages ids resulting from a solr query:

```sh
ENV=dev pipenv run python ./manage.py addtocollectionfromtrpassagesquery local-dg-abcde "cluster_id_s:tr-nobp-all-v01-c8590083914"
```

Stop a specific job from command line:

```sh
ENV=dev pipenv run python ./manage.py stopjob 1234
```

## Use in production

Please check the included Dockerfile to generate your own docker image or use the docker image available on impresso dockerhub.

Test image locally:

```
make run
```

### Note on collection syncronisation between indices.

Collections are simple identifiers assigned to a set of newspaper articles and stored in the `search` index. However, other indices (e.g. `tr_passages`) can be linked to a collection to allow cross-indices search.
The task of creating a collection is a long running one because it uses a solr search query to filter the `content items` and a solr update request to add the collection tag to the various indices. Every search request is limited to `settings.IMPRESSO_SOLR_EXEC_LIMIT` rows (100 by default) and the number of loops is limited to the user `max_allowed_loops` parameter in the database and in general cannot be higher of `settings.IMPRESSO_SOLR_MAX_LOOPS` (100 recommended for a total of 100\*100 rows default max). Set both parameters in the `.env` file accordingly.

The task of creating a collection is delegated to the _Celery_ task manager and a `Job` instance stored in the database is assigned to the task to allow the follow-up of the task progress. The task is executed asynchronously. In the future releases, the user will be notified via email when the task is completed (still todo).

## Project

The 'impresso - Media Monitoring of the Past' project is funded by the Swiss National Science Foundation (SNSF) under grant number [CRSII5_173719](http://p3.snf.ch/project-173719) (Sinergia program). The project aims at developing tools to process and explore large-scale collections of historical newspapers, and at studying the impact of this new tooling on historical research practices. More information at https://impresso-project.ch.

## License

Copyright (C) 2020 The _impresso_ team. Contributors to this program include: [Daniele Guido](https://github.com/danieleguido), [Roman Kalyakin](https://github.com/theorm).
This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but without any warranty; without even the implied warranty of merchantability or fitness for a particular purpose. See the [GNU Affero General Public License](https://github.com/impresso/impresso-user-admin/blob/master/LICENSE) for more details.
