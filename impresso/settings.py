"""
Django settings for impresso project.

Generated by 'django-admin startproject' using Django 2.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

VERSION = (1, 1, 0)

import os
from .base import get_env_variable

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable('SECRET_KEY')

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

MEDIA_URL = get_env_variable('MEDIA_URL', '/media/')
MEDIA_ROOT = get_env_variable('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))
LOGS_ROOT = get_env_variable('LOGS_ROOT', os.path.join(BASE_DIR, 'logs'))


# Celery
REDIS_HOST = get_env_variable('REDIS_HOST', 'localhost')
CELERY_BROKER_URL = f'redis://{REDIS_HOST}/4'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}/5'
CELERYD_PREFETCH_MULTIPLIER = 2
CELERYD_CONCURRENCY = 2

# Solr
IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS = {
    'id': 'uid',
    'item_type_s': 'type',
    'lg_s': 'language',
    'title_txt_fr': 'title',
    'title_txt_de': 'title',
    'title_txt_en': 'title',
    'content_txt_fr': 'content',
    'content_txt_de': 'content',
    'content_txt_en': 'content',
    'content_length_i': 'size',
    'meta_country_code_s': 'country',
    'meta_year_i': 'year',
    'meta_journal_s': 'newspaper',
    'meta_issue_id_s': 'issue',
    'page_id_ss': 'pages_uids',
    'page_nb_is': 'pages',
    'nb_pages_i': 'nb_pages',
    'front_b': 'is_on_front',
    'meta_date_dt': 'date',
    'pers_mentions': 'persons_mentioned',
    'loc_mentions': 'locations_mentioned',
    'access_right_s': 'access_right',
    'meta_partnerid_s': 'content_provider',
    'score': 'relevance',
    'exportable_plain': 'is_content_available',
}

IMPRESSO_SOLR_URL_SELECT = os.path.join(get_env_variable('IMPRESSO_SOLR_URL'), 'select')
IMPRESSO_SOLR_URL_UPDATE = os.path.join(get_env_variable('IMPRESSO_SOLR_URL'), 'update')
IMPRESSO_SOLR_USER = get_env_variable('IMPRESSO_SOLR_USER')
IMPRESSO_SOLR_USER_WRITE = get_env_variable('IMPRESSO_SOLR_USER_WRITE')
IMPRESSO_SOLR_PASSWORD = get_env_variable('IMPRESSO_SOLR_PASSWORD')
IMPRESSO_SOLR_PASSWORD_WRITE = get_env_variable('IMPRESSO_SOLR_PASSWORD_WRITE')
IMPRESSO_SOLR_AUTH = (IMPRESSO_SOLR_USER, IMPRESSO_SOLR_PASSWORD,)
IMPRESSO_SOLR_AUTH_WRITE = (IMPRESSO_SOLR_USER_WRITE, IMPRESSO_SOLR_PASSWORD_WRITE,)
IMPRESSO_SOLR_ID_FIELD = get_env_variable('IMPRESSO_SOLR_ID_FIELD', 'id')
IMPRESSO_SOLR_FIELDS = get_env_variable('IMPRESSO_SOLR_EXPORTS_FIELD', 'id,meta_journal_s,lg_s,title_txt_de,title_txt_fr,content_txt_de,content_txt_fr,content_length_i,meta_date_dt,meta_year_i,meta_issue_id_s,page_nb_is,nb_pages_i,front_b,meta_country_code_s,pers_mentions,loc_mentions,access_right_s,meta_partnerid_s,exportable_plain,score')
IMPRESSO_SOLR_ARTICLE_PROPS = get_env_variable('IMPRESSO_SOLR_EXPORTS_FIELD', 'uid,type,language,title,size,country,newspaper,issue,pages,nb_pages,relevance,year,is_on_front,date,persons_mentioned,locations_mentioned,content,access_right,content_provider,is_content_available')

IMPRESSO_SOLR_EXEC_MAX_LOOPS = int(get_env_variable('IMPRESSO_SOLR_EXEC_MAX_LOOPS', 100000)) # aka 500000 docs
IMPRESSO_SOLR_EXEC_LIMIT = int(get_env_variable('IMPRESSO_SOLR_EXEC_LIMIT', 100))

IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR = int(get_env_variable('IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR', 1871))

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            # exact format is not important, this is the minimum information
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 15728640,  # 1024 * 1024 * 15B = 15MB
            'filename': os.path.join(LOGS_ROOT, 'debug.log'),
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'console': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'impresso': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        }
    },
}
