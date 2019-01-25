"""
Django settings for impresso project.

Generated by 'django-admin startproject' using Django 2.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
from .base import get_env_variable

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'xvqp74e(#pd**ubd*3yv$+kf$li8*ml+!r_=_&$5vbu-1yww$g'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_variable('DEBUG') == 'True'

ALLOWED_HOSTS = [ get_env_variable('ALLOWED_HOSTS') ]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'impresso',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'impresso.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'impresso.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': get_env_variable('IMPRESSO_DB_ENGINE'),
        'NAME': get_env_variable('IMPRESSO_DB_NAME'),
        'USER': get_env_variable('IMPRESSO_DB_USER'),
        'PASSWORD': get_env_variable('IMPRESSO_DB_PASSWORD'),
        'HOST': get_env_variable('IMPRESSO_DB_HOST'),
        'PORT': get_env_variable('IMPRESSO_DB_PORT')
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
STATIC_URL = get_env_variable('STATIC_URL', '/static/')
STATIC_ROOT = get_env_variable('STATIC_ROOT', os.path.join(BASE_DIR, 'static'))


# Celery
CELERY_BROKER_URL = 'redis://localhost/4'
CELERY_RESULT_BACKEND = 'redis://localhost/5'
CELERYD_PREFETCH_MULTIPLIER = 2
CELERYD_CONCURRENCY = 2

# Solr
IMPRESSO_SOLR_URL_SELECT = os.path.join(get_env_variable('IMPRESSO_SOLR_URL'), 'select')
IMPRESSO_SOLR_URL_UPDATE = os.path.join(get_env_variable('IMPRESSO_SOLR_URL'), 'update')
IMPRESSO_SOLR_USER = get_env_variable('IMPRESSO_SOLR_USER')
IMPRESSO_SOLR_USER_WRITE = get_env_variable('IMPRESSO_SOLR_USER_WRITE')
IMPRESSO_SOLR_PASSWORD = get_env_variable('IMPRESSO_SOLR_PASSWORD')
IMPRESSO_SOLR_PASSWORD_WRITE = get_env_variable('IMPRESSO_SOLR_PASSWORD_WRITE')
IMPRESSO_SOLR_AUTH = (IMPRESSO_SOLR_USER, IMPRESSO_SOLR_PASSWORD,)
IMPRESSO_SOLR_AUTH_WRITE = (IMPRESSO_SOLR_USER_WRITE, IMPRESSO_SOLR_PASSWORD_WRITE,)
IMPRESSO_SOLR_ID_FIELD = get_env_variable('IMPRESSO_SOLR_ID_FIELD', 'id')
IMPRESSO_SOLR_EXEC_MAX_LOOPS = int(get_env_variable('IMPRESSO_SOLR_EXEC_MAX_LOOPS', 100000)) # aka 500000 docs
IMPRESSO_SOLR_EXEC_LIMIT = int(get_env_variable('IMPRESSO_SOLR_EXEC_LIMIT', 100)) 
