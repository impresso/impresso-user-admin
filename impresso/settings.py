import os
from .base import get_env_variable

VERSION = (2, 2, 0)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_variable("DEBUG") == "True"

ALLOWED_HOSTS = [get_env_variable("ALLOWED_HOSTS")]

CSRF_TRUSTED_ORIGINS = get_env_variable("CSRF_TRUSTED_ORIGINS", "").split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_registration",
    "impresso.apps.ImpressoConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "impresso.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "impresso.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": get_env_variable("IMPRESSO_DB_ENGINE"),
        "NAME": get_env_variable("IMPRESSO_DB_NAME"),
        "USER": get_env_variable("IMPRESSO_DB_USER"),
        "PASSWORD": get_env_variable("IMPRESSO_DB_PASSWORD"),
        "HOST": get_env_variable("IMPRESSO_DB_HOST"),
        "PORT": get_env_variable("IMPRESSO_DB_PORT"),
        "TEST": {
            "NAME": get_env_variable("IMPRESSO_DB_NAME_TEST", "impresso_test"),
            "ENGINE": get_env_variable(
                "IMPRESSO_DB_ENGINE_TEST", "django.db.backends.sqlite3"
            ),
        },
        "OPTIONS": {"ssl": {"rejectUnauthorized": False}},
    }
}
import sys

if "test" in sys.argv:
    DATABASES["default"]["ENGINE"] = "django.db.backends.sqlite3"
    DATABASES["default"]["TEST"]["NAME"] = ":memory:"
    DATABASES["default"]["OPTIONS"] = {"timeout": 20}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
STATIC_URL = get_env_variable("STATIC_URL", "/static/")
STATIC_ROOT = get_env_variable("STATIC_ROOT", os.path.join(BASE_DIR, "static"))

MEDIA_URL = get_env_variable("MEDIA_URL", "/media/")
MEDIA_ROOT = get_env_variable("MEDIA_ROOT", os.path.join(BASE_DIR, "media"))
LOGS_ROOT = get_env_variable("LOGS_ROOT", os.path.join(BASE_DIR, "logs"))

# django registration
ACCOUNT_ACTIVATION_DAYS = int(get_env_variable("ACCOUNT_ACTIVATION_DAYS", "7"))

# email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# 'django.core.mail.backends.locmem.EmailBackend'
EMAIL_HOST = get_env_variable("EMAIL_HOST", "smtp.")
EMAIL_PORT = get_env_variable("EMAIL_PORT", 0)
DEFAULT_FROM_EMAIL = get_env_variable("DEFAULT_FROM_EMAIL", "info@")
# Celery
REDIS_HOST = get_env_variable("REDIS_HOST", "localhost:6379")
CELERY_BROKER_URL = f"redis://{REDIS_HOST}/4"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}/5"
CELERYD_PREFETCH_MULTIPLIER = 2
CELERYD_CONCURRENCY = 2
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = (
    get_env_variable("CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP", False) == "True"
)


# Solr
# this is the complete mapping. Please check that the values of your IMPRESSO_SOLR_FIELDS
# are correctly spelled, as well as the IMPRESSO_SOLR_ARTICLE_PROPS
# The values starting with an underscore are not returned to user but used internally
IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS = {
    "id": "uid",
    "item_type_s": "type",
    "lg_s": "language",
    "title_txt_fr": "title",
    "title_txt_de": "title",
    "title_txt_en": "title",
    "content_txt_fr": "content",
    "content_txt_de": "content",
    "content_txt_en": "content",
    "content_length_i": "size",
    "meta_country_code_s": "country",
    "meta_province_code_s": "province",
    "meta_periodicity_s": "periodicity",
    "meta_year_i": "year",
    "meta_journal_s": "newspaper",
    "meta_issue_id_s": "issue",
    "meta_partnerid_s": "content_provider",
    "meta_topics_s": "newspaper_topics",
    "meta_polorient_s": "newspaper_political_orientation",
    "olr_b": "is_olr",
    # "page_id_ss": "pages_uids",
    "page_nb_is": "pages",
    "nb_pages_i": "nb_pages",
    "front_b": "is_on_front_page",
    "meta_date_dt": "date",
    "pers_mentions": "persons_mentioned",
    "loc_mentions": "locations_mentioned",
    "nag_mentions": "newsagencies_mentioned",
    "access_right_s": "access_right",
    "score": "relevance",
    "exportable_plain": "is_content_available",
    "ucoll_ss": "collections",
    "topics_dpfs": "topics",
    # "cc_b": "cc_b",
    # bitmap keys, we still maintain both for compatibility reasons
    "bm_get_tr_s": "_bm_get_tr_s",
    "bm_get_tr_i": "_bm_get_tr_i",
    # note: `_bin` fields are deprecated as it would require a custom JSONEncoder (and regexp within the raw_decode, which is not the best idea)
    # "bm_get_tr_bin": "_bm_get_tr_s_bin",
}

IMPRESSO_SOLR_URL_SELECT = os.path.join(get_env_variable("IMPRESSO_SOLR_URL"), "select")
IMPRESSO_SOLR_URL_UPDATE = os.path.join(get_env_variable("IMPRESSO_SOLR_URL"), "update")
IMPRESSO_SOLR_USER = get_env_variable("IMPRESSO_SOLR_USER")
IMPRESSO_SOLR_USER_WRITE = get_env_variable("IMPRESSO_SOLR_USER_WRITE")
IMPRESSO_SOLR_PASSWORD = get_env_variable("IMPRESSO_SOLR_PASSWORD")
IMPRESSO_SOLR_PASSWORD_WRITE = get_env_variable("IMPRESSO_SOLR_PASSWORD_WRITE")
IMPRESSO_SOLR_AUTH = (
    IMPRESSO_SOLR_USER,
    IMPRESSO_SOLR_PASSWORD,
)
IMPRESSO_SOLR_AUTH_WRITE = (
    IMPRESSO_SOLR_USER_WRITE,
    IMPRESSO_SOLR_PASSWORD_WRITE,
)
IMPRESSO_SOLR_ID_FIELD = get_env_variable("IMPRESSO_SOLR_ID_FIELD", "id")
IMPRESSO_SOLR_FIELDS = get_env_variable(
    "IMPRESSO_SOLR_FIELDS",
    ",".join(IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS.keys()),
)

# check that settings.IMPRESSO_SOLR_FIELDS is set according to the fields specified in the mapping
# settings.IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS.
# raise an error if not
IMPRESSO_SOLR_FIELDS_AS_LIST = IMPRESSO_SOLR_FIELDS.split(",")
# check that every item in impresso_solr_fields is in the keys of IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS
impresso_solr_fields_to_article_props_keys = (
    IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS.keys()
)
for field in IMPRESSO_SOLR_FIELDS_AS_LIST:
    if field not in impresso_solr_fields_to_article_props_keys:
        raise ValueError(
            f"IMPRESSO_SOLR_FIELDS and IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS do not match: check field {field}"
        )

IMPRESSO_SOLR_ARTICLE_PROPS = sorted(
    list(
        set(
            [
                IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS.get(x)
                for x in IMPRESSO_SOLR_FIELDS_AS_LIST
            ]
        )
    ),
    key=lambda x: (x != "uid", x),
)


IMPRESSO_SOLR_EXEC_MAX_LOOPS = int(
    get_env_variable("IMPRESSO_SOLR_EXEC_MAX_LOOPS", 100000)
)  # aka 500000 docs
IMPRESSO_SOLR_EXEC_LIMIT = int(get_env_variable("IMPRESSO_SOLR_EXEC_LIMIT", 100))

IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR = int(
    get_env_variable("IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR", 1871)
)
IMPRESSO_CONTENT_DOWNLOAD_DISCLAIMER = get_env_variable(
    "IMPRESSO_CONTENT_DOWNLOAD_DISCLAIMER",
    "This data is provided for research purposes only.",
)
# SOLR passages. Requires IMPRESSO_SOLR_PASSAGES_URL env variables.
IMPRESSO_SOLR_PASSAGES_URL_SELECT = os.path.join(
    get_env_variable("IMPRESSO_SOLR_PASSAGES_URL"), "select"
)

IMPRESSO_SOLR_PASSAGES_URL_UPDATE = os.path.join(
    get_env_variable("IMPRESSO_SOLR_PASSAGES_URL"), "update"
)

IMPRESSO_GIT_TAG = get_env_variable("IMPRESSO_GIT_TAG", "?")
IMPRESSO_GIT_BRANCH = get_env_variable("IMPRESSO_GIT_BRANCH", "?")
IMPRESSO_GIT_REVISION = get_env_variable("IMPRESSO_GIT_REVISION", "?")

IMPRESSO_GROUP_USER_PLAN_BASIC = "plan-basic"
IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL = "plan-educational"
IMPRESSO_GROUP_USER_PLAN_RESEARCHER = "plan-researcher"
IMPRESSO_GROUP_USER_PLAN_REQUEST_EDUCATIONAL = "request-plan-educational"
IMPRESSO_GROUP_USER_PLAN_REQUEST_RESEARCHER = "request-plan-researcher"

IMPRESSO_GROUP_USERS_AVAILABLE_PLANS = [
    IMPRESSO_GROUP_USER_PLAN_BASIC,
    IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL,
    IMPRESSO_GROUP_USER_PLAN_RESEARCHER,
]

IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL = "Basic User Plan"
IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL = "Student User Plan"
IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL = "Academic User Plan"


IMPRESSO_DEFAULT_GROUP_USERS = (
    (IMPRESSO_GROUP_USER_PLAN_REQUEST_EDUCATIONAL, "Request Student User Plan"),
    (IMPRESSO_GROUP_USER_PLAN_REQUEST_RESEARCHER, "Request Academic User Plan"),
    (IMPRESSO_GROUP_USER_PLAN_BASIC, IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL),
    (IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL, IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL),
    (IMPRESSO_GROUP_USER_PLAN_RESEARCHER, IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL),
)


IMPRESSO_EMAIL_SUBJECT_AFTER_USER_REGISTRATION_PLAN_BASIC = "Access to Impresso"
IMPRESSO_EMAIL_SUBJECT_AFTER_USER_REGISTRATION_PLAN_EDUCATIONAL = (
    "Access to Impresso - Student User Plan"
)
IMPRESSO_EMAIL_SUBJECT_AFTER_USER_REGISTRATION_PLAN_RESEARCHER = (
    "Access to Impresso - Academic User Plan"
)
IMPRESSO_EMAIL_SUBJECT_PASSWORD_RESET = (
    "Password reset request for your Impresso account"
)

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            # exact format is not important, this is the minimum information
            "format": "%(asctime)s [%(name)s.%(funcName)s:%(lineno)s] %(levelname)-8s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 15728640,  # 1024 * 1024 * 15B = 15MB
            "filename": os.path.join(LOGS_ROOT, "debug.log"),
            "formatter": "verbose",
        },
    },
    "loggers": {
        "impresso.management.commands": {
            "level": "INFO",
            "handlers": ["console"],
        },
        "console": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "impresso": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "impresso.utils": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
