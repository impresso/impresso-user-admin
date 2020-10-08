# impresso-user-admin

A basic django application to manage user-related information contained in [Impresso's Master DB](https://github.com/impresso/impresso-master-db).


## installation on CENTOS 7
Install python 3.6 following [digitalocean tutorial](https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-local-programming-environment-on-centos-7)

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

### setup impresso virtualenv
We assume that virtualenvs are stored in user home dir:
```
cd ~/.virtualenvs
python3.6 -m venv impresso
source impresso/bin/activate
```
with **pipenv** simply do:
```
cd /path/to/impresso-user-admin/
pipenv install --dev
```
and your're all set. Activate pipenv virtualenv with `pipenv shell`.


### setup dotenv files
Django settings.py is enriched via `dotenv` files, special and simple configuration files.
We use a dotenv file to store sensitive settings and to store settings for a specific environment ("development" or "production"). A dotenv file is parsed when we set its prefix in the `ENV` environment variable, that is, `.dev.env` is used when we have `ENV=dev`:
```
ENV=dev ./manage.py runserver
```
This command runs the development server enriching the settings file with the cofiguration stored in the `.dev.env` file.
Please use the `.example.env` file as astarting point to generate specific environment configuration (e.g. `prod`or `sandbox`).


### add new superuser
```
cd /path/to/impresso-user-admin/
source ~/.virtualenvs/impresso/bin/activate
ENV=dev ./manage.py createsuperuser

### setup celery
Once pip installed celery:

```

### django in production
Set the `STATIC_ROOT` variable in your `dotenv` file as absolute path.
If you skip this passage the static folder will be

```
ENV=dev ./manage.py collectstatic
```


### Index collections in SOLR with celery (local test only)
In production, we run the celery worker as a subprocess of impresso-user-admin vassal.
Check UWSGI logging with:
```
tail -f /var/log/uwsgi-emperor.log
```
In your local context, you may not have uwsgi running.  
According to your env file, you can launch the worker using `celery` command:
```
ENV=local celery -A impresso worker -l info
```

Index collection using:
```
ENV=local ./manage.py synccollection test-abcd
```
Or using pipenv:
```
ENV=local pipenv run ./manage.py synccollection test-abcd
```

Export query as csv using (first argument being `user_id`):
```
ENV=local ./manage.py exportqueryascsv 1 "content_txt_fr:\"premier ministre portugais\""
```

# UWSGI installation

Install uwsgi in your system: `pip install uwsgi` from inside `pipenv shell`.
The uwsgi file should run the `celery` worker along with the main app from within the virtual enviromnent,
so the resulting ini file would be:

```
[uwsgi]
uid = impresso
# www-data
gid = impresso
# www-data


chdir        = /path/to/impresso-user-admin
module       = impresso.wsgi:application
home         = /path/to/.virtualenvs/impresso
master       = true
processes    = 2
socket       = /path/to/impresso-user-admin.wsgi.sock
chmod-socket = 777
env          = DJANGO_SETTINGS_MODULE=impresso.settings
env          = ENV=prod
vacuum       = true

safe-pidfile = /path/to/impresso-user-admin.pid
harakiri = 20
attach-daemon2= cmd=ENV=prod /path/to/.virtualenvs/impresso/bin/celery -A impresso worker -l info -c 1
```   
Note that the property `home` points to the virtual environment folder.                                                                                                         
## Project
The 'impresso - Media Monitoring of the Past' project is funded by the Swiss National Science Foundation (SNSF) under  grant number [CRSII5_173719](http://p3.snf.ch/project-173719) (Sinergia program). The project aims at developing tools to process and explore large-scale collections of historical newspapers, and at studying the impact of this new tooling on historical research practices. More information at https://impresso-project.ch.
## License
Copyright (C) 2020  The *impresso* team. Contributors to this program include: [Daniele Guido](https://github.com/danieleguido), [Roman Kalyakin](https://github.com/theorm).
This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. 
This program is distributed in the hope that it will be useful, but without any warranty; without even the implied warranty of merchantability or fitness for a particular purpose. See the [GNU Affero General Public License](https://github.com/impresso/impresso-pycommons/blob/master/LICENSE***EDIT LINK****) for more details.
