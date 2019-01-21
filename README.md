# impresso-user-admin

A basic django application to manage user-related information contained in [Impresso's Master DB](https://github.com/impresso/impresso-master-db).


## installation on CENTOS 7
Install python 3.6 following [digitalocean tutorial](https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-local-programming-environment-on-centos-7)

### setup impresso virtualenv
```
cd .virtualenvs
python3.6 -m venv impresso
source impresso/bin/activate
```

### setup env files
We use env files to inject sensitive configuration into `settings.js`.

```
ENV=dev python manage.py runserver
```
will load configuration from `.dev.env` file

basic configuration for the `*.env` files can be found in the `.example.env`

### setup celery
Once pip installed celery:

```
ENV=dev celery -A impresso worker -l info
```
