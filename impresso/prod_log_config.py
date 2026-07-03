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
        # Django's own logs (requests, server, security, etc.)
        "django": {"handlers": ["default"], "level": "INFO", "propagate": False},
        # This project's app code
        "impresso": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
    # Everything else falls through to root, which otherwise has no handler
    # and logs plain text.
    "root": {"handlers": ["default"], "level": "INFO"},
}
