# impresso-user-admin

A basic django application to manage user-related information contained in [Impresso's Master DB](https://github.com/impresso/impresso-master-db).


## installation on CENTOS 7
Install python 3.6 following [digitalocean tutorial](https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-local-programming-environment-on-centos-7)

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
``
