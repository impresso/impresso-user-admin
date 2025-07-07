import os
import socket

from impresso.utils.proxy import with_optional_proxy
from .base import get_env_variable
from django import __version__ as django_version

import MySQLdb as Database

Database.connect = with_optional_proxy(Database.connect)

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
    "unfold",  # before django.contrib.admin
    "unfold.contrib.filters",  # optional, if special filters are needed
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",  # optional, if django-simple-history package is
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
CELERYD_PREFETCH_MULTIPLIER = int(get_env_variable("CELERYD_PREFETCH_MULTIPLIER", "1"))
CELERYD_CONCURRENCY = int(get_env_variable("CELERYD_CONCURRENCY", "1"))
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = (
    get_env_variable("CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP", False) == "True"
)

IMPRESSO_BASE_URL = get_env_variable("IMPRESSO_BASE_URL", "https://impresso-project.ch")

# Solr
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
IMPRESSO_SOLR_FL_TRANSCRIPT_BM = get_env_variable(
    "IMPRESSO_SOLR_FL_TRANSCRIPT_BM_FIELD", "rights_bm_get_tr_l"
)
IMPRESSO_SOLR_FL_COPYRIGHT = get_env_variable(
    "IMPRESSO_SOLR_FL_COPYRIGHT", "rights_copyright_s"
)
# Full mapping
IMPRESSO_SOLR_FL_ID = get_env_variable("IMPRESSO_SOLR_FL_ID", "id")
IMPRESSO_SOLR_FL_ID_LABEL = "uid"

IMPRESSO_SOLR_FL_TYPE = "item_type_s"
IMPRESSO_SOLR_FL_TYPE_LABEL = "type"

IMPRESSO_SOLR_FL_TITLE_LABEL = "title"  # Multilingual field

IMPRESSO_SOLR_FL_EXCERPT = "snippet_plain"
IMPRESSO_SOLR_FL_EXCERPT_LABEL = "excerpt"

IMPRESSO_SOLR_FL_COUNTRY = "meta_country_code_s"
IMPRESSO_SOLR_FL_COUNTRY_LABEL = "countryCode"
# province
IMPRESSO_SOLR_FL_PROVINCE = "meta_province_code_s"
IMPRESSO_SOLR_FL_PROVINCE_LABEL = "provinceCode"
# periodicity
IMPRESSO_SOLR_FL_PERIODICITY = "meta_periodicity_s"
IMPRESSO_SOLR_FL_PERIODICITY_LABEL = "periodicity"

IMPRESSO_SOLR_FL_LANGUAGE = "lg_s"
IMPRESSO_SOLR_FL_LANGUAGE_LABEL = "languageCode"

IMPRESSO_SOLR_FL_CONTENT_LABEL = "transcript"

IMPRESSO_SOLR_FL_CONTENT_LENGTH = "content_length_i"
IMPRESSO_SOLR_FL_CONTENT_LENGTH_LABEL = "transcriptLength"
IMPRESSO_SOLR_FL_YEAR = "meta_year_i"
IMPRESSO_SOLR_FL_YEAR_LABEL = "year"
IMPRESSO_SOLR_FL_TOTAL_PAGES = "nb_pages_i"
IMPRESSO_SOLR_FL_TOTAL_PAGES_LABEL = "totalPages"

IMPRESSO_SOLR_FL_DATA_PROVIDER = "meta_partnerid_s"
IMPRESSO_SOLR_FL_DATA_PROVIDER_LABEL = "dataProviderCode"

IMPRESSO_SOLR_FL_MEDIA_CODE = "meta_journal_s"
IMPRESSO_SOLR_FL_MEDIA_CODE_LABEL = "mediaCode"
# media political orientation
IMPRESSO_SOLR_FL_MEDIA_POLITICAL_ORIENTATION = "meta_polorient_s"
IMPRESSO_SOLR_FL_MEDIA_POLITICAL_ORIENTATION_LABEL = "mediaPoliticalOrientation"
# media topics
IMPRESSO_SOLR_FL_MEDIA_TOPICS = "meta_topics_s"
IMPRESSO_SOLR_FL_MEDIA_TOPICS_LABEL = "mediaTopics"
# date
IMPRESSO_SOLR_FL_DATE = "meta_date_dt"
IMPRESSO_SOLR_FL_DATE_LABEL = "publicationDate"
# front page
IMPRESSO_SOLR_FL_FRONT_PAGE = "front_b"
IMPRESSO_SOLR_FL_FRONT_PAGE_LABEL = "isOnFrontPage"
# this is the complete mapping. Please check that the values of your IMPRESSO_SOLR_FIELDS
# are correctly spelled, as well as the IMPRESSO_SOLR_ARTICLE_PROPS
# The values starting with an underscore "_"
# are NOT returned to users, but are used for internal purposes
# E.G "rights_data_domain_s":"prt",
# "rights_copyright_s":"in_cpy",
# "rights_perm_use_explore_plain":"prs-rsh-edu",
# "rights_perm_use_get_tr_plain":"rsh",
# "rights_perm_use_get_img_plain":"rsh",
# "rights_bm_explore_l":10,
# "rights_bm_get_tr_l":1000,
# "rights_bm_get_img_l":1000,
IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS = {
    IMPRESSO_SOLR_FL_ID: IMPRESSO_SOLR_FL_ID_LABEL,
    IMPRESSO_SOLR_FL_TYPE: IMPRESSO_SOLR_FL_TYPE_LABEL,
    IMPRESSO_SOLR_FL_LANGUAGE: IMPRESSO_SOLR_FL_LANGUAGE_LABEL,
    "title_txt_fr": IMPRESSO_SOLR_FL_TITLE_LABEL,
    "title_txt_de": IMPRESSO_SOLR_FL_TITLE_LABEL,
    "title_txt_en": IMPRESSO_SOLR_FL_TITLE_LABEL,
    "content_txt_fr": IMPRESSO_SOLR_FL_CONTENT_LABEL,
    "content_txt_de": IMPRESSO_SOLR_FL_CONTENT_LABEL,
    "content_txt_en": IMPRESSO_SOLR_FL_CONTENT_LABEL,
    IMPRESSO_SOLR_FL_EXCERPT: IMPRESSO_SOLR_FL_EXCERPT_LABEL,
    IMPRESSO_SOLR_FL_CONTENT_LENGTH: IMPRESSO_SOLR_FL_CONTENT_LENGTH_LABEL,
    IMPRESSO_SOLR_FL_COUNTRY: IMPRESSO_SOLR_FL_COUNTRY_LABEL,
    IMPRESSO_SOLR_FL_PROVINCE: IMPRESSO_SOLR_FL_PROVINCE_LABEL,
    IMPRESSO_SOLR_FL_PERIODICITY: IMPRESSO_SOLR_FL_PERIODICITY_LABEL,
    IMPRESSO_SOLR_FL_YEAR: IMPRESSO_SOLR_FL_YEAR_LABEL,
    IMPRESSO_SOLR_FL_MEDIA_CODE: IMPRESSO_SOLR_FL_MEDIA_CODE_LABEL,
    "meta_issue_id_s": "issue",
    IMPRESSO_SOLR_FL_DATA_PROVIDER: IMPRESSO_SOLR_FL_DATA_PROVIDER_LABEL,
    IMPRESSO_SOLR_FL_MEDIA_TOPICS: IMPRESSO_SOLR_FL_MEDIA_TOPICS_LABEL,
    IMPRESSO_SOLR_FL_MEDIA_POLITICAL_ORIENTATION: IMPRESSO_SOLR_FL_MEDIA_POLITICAL_ORIENTATION_LABEL,
    "olr_b": "is_olr",
    # "page_id_ss": "pages_uids",
    "page_nb_is": "pages",
    IMPRESSO_SOLR_FL_TOTAL_PAGES: IMPRESSO_SOLR_FL_TOTAL_PAGES_LABEL,
    IMPRESSO_SOLR_FL_FRONT_PAGE: IMPRESSO_SOLR_FL_FRONT_PAGE_LABEL,
    IMPRESSO_SOLR_FL_DATE: IMPRESSO_SOLR_FL_DATE_LABEL,
    "pers_mentions": "persons_mentioned",
    "loc_mentions": "locations_mentioned",
    "nag_mentions": "newsagencies_mentioned",
    "access_right_s": "access_right",
    "score": "relevance",
    "exportable_plain": "is_content_available",
    "ucoll_ss": "collections",
    "topics_dpfs": "topics",
    IMPRESSO_SOLR_FL_COPYRIGHT: f"_{IMPRESSO_SOLR_FL_COPYRIGHT}",
    IMPRESSO_SOLR_FL_TRANSCRIPT_BM: f"_{IMPRESSO_SOLR_FL_TRANSCRIPT_BM}",
}
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

IMPRESSO_CONTENT_REDACTED_LABEL = "[Copyright restricted]"
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

IMPRESSO_GIT_TAG = get_env_variable("IMPRESSO_GIT_TAG", ".".join(map(str, VERSION)))
IMPRESSO_GIT_BRANCH = get_env_variable("IMPRESSO_GIT_BRANCH", "?")
IMPRESSO_GIT_REVISION = get_env_variable("IMPRESSO_GIT_REVISION", "?")

IMPRESSO_GROUP_USER_PLAN_BASIC = "plan-basic"
IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL = "plan-educational"
IMPRESSO_GROUP_USER_PLAN_RESEARCHER = "plan-researcher"
IMPRESSO_GROUP_USER_PLAN_REQUEST_EDUCATIONAL = "request-plan-educational"
IMPRESSO_GROUP_USER_PLAN_REQUEST_RESEARCHER = "request-plan-researcher"
IMPRESSO_GROUP_USER_PLAN_NO_REDACTION = "NoRedaction"

IMPRESSO_GROUP_USERS_AVAILABLE_PLANS = [
    IMPRESSO_GROUP_USER_PLAN_BASIC,
    IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL,
    IMPRESSO_GROUP_USER_PLAN_RESEARCHER,
]
IMPRESSO_GROUP_USER_PLAN_NONE_LABEL = "No plan selected"
IMPRESSO_GROUP_USER_PLAN_GUEST_LABEL = "Guest (Terms of use not accepted)"
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


UNFOLD = {
    "SITE_TITLE": "Impresso User Admin",
    "SITE_HEADER": "Impresso User Admin",
    "SITE_SUBHEADER": f"v.{IMPRESSO_GIT_TAG} - Django v.{django_version}",
    "SIDEBAR": {
        "show_search": True,  # Search in applications and models names
    },
    #  "COLORS": {
    #     "base": {
    #         "50": "249 250 251",
    #         "100": "243 244 246",
    #         "200": "229 231 235",
    #         "300": "209 213 219",
    #         "400": "156 163 175",
    #         "500": "107 114 128",
    #         "600": "75 85 99",
    #         "700": "55 65 81",
    #         "800": "31 41 55",
    #         "900": "17 24 39",
    #         "950": "3 7 18",
    #     },
    #     "primary": {
    #         "500": "0, 102, 255",
    #         "600": "52, 58, 64",
    #         "700": "45, 55, 72",
    #         "800": "30, 41, 59",
    #         "900": "15, 23, 42",
    #         "950": "3, 0, 15",
    #     },
    #  }
}
