import os
import sys

# True when running under `manage.py test` or pytest, however invoked
RUNNING_TESTS = "test" in sys.argv or "pytest" in sys.modules

# Opt-in escape hatch: TEST_LOGS=1 ./manage.py test to see logs anyway
SHOW_TEST_LOGS = os.environ.get("TEST_LOGS", "") == "1"

LOG_LEVEL = "CRITICAL" if (RUNNING_TESTS and not SHOW_TEST_LOGS) else "INFO"


CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            # Update this string to the new modern import path:
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(filename)s %(lineno)d",
        },
    },
    "handlers": {
        "default": {
            "formatter": "json",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        # Django's own logs (requests, security, etc.)
        "django": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
        # Django's DEFAULT_LOGGING gives this its own handler with
        # propagate=False, so it must be overridden explicitly or runserver's
        # access log lines bypass the "django" logger above entirely.
        "django.server": {
            "handlers": ["default"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # This project's app code
        "impresso": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
    },
    # Everything else falls through to root, which otherwise has no handler
    # and logs plain text.
    "root": {"handlers": ["default"], "level": LOG_LEVEL},
}
