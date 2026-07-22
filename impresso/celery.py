from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import setup_logging
import pymysql

# use pymysql isntead of MysQLdb
pymysql.version_info = (1, 4, 6, 'final', 0)  # change mysqlclient version
pymysql.install_as_MySQLdb()

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'impresso.settings')

app = Celery('impresso')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@setup_logging.connect
def use_django_logging(**kwargs):
    # Celery always resets the "celery"/"celery.task"/"celery.redirected"
    # loggers with its own plain-text handlers on startup, regardless of
    # worker_hijack_root_logger (that flag only covers the root logger).
    # Connecting to this signal makes Celery skip its own logging setup
    # entirely, so Django's LOGGING config (JSON in production) is what
    # actually ends up configured.
    from django.conf import settings
    from django.utils.log import configure_logging

    configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
