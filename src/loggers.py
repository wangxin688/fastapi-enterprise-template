import logging
from collections.abc import Hashable
from logging import LogRecord, setLogRecordFactory
from logging.config import dictConfig

from src._types import P
from src.context import request_id_ctx


class LogExtraFactory(LogRecord):
    def __init__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        request_id = request_id_ctx.get() or "N/A"
        self.__dict__["request_id"] = request_id


LOGGING = {
    "version": 1,
    "disable_existing_loggers": 0,
    "formatters": {
        "default": {
            "format": (
                "%(asctime)s | %(levelname)s | %(request_id)% | %(filename)s:%(funcName)s:%(lineno)d | %(message)s"
            ),
            "celery": {
                "format": (
                    "%(asctime)s | %(levelname)s | %(request_id)% [%(celery_parent_id)s-%(celery_current_id)s] |"
                    " %(filename)s:%(funcName)s:%(lineno)d | %(message)s"
                ),
            },
        },
    },
    "handlers": {
        "stdout": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "gunicorn.access": {"handlers": ["stdout"], "propagate": True, "level": "DEBUG"},
        "guncorn.error": {"handlers": ["stdout"], "propagate": True, "level": "DEBUG"},
        "celery": {"handlers": ["stdout"], "propagate": True, "level": "DEBUG"},
        "celery.app.trace": {"handlers": ["stdout"], "propagate": False, "level": "DEBUG"},
        "": {"handlers": ["stdout"], "propagate": False, "level": "DEBUG"},
    },
}


def configure_logger(config: Hashable | None = None) -> None:
    if config is None:
        config = LOGGING
    dictConfig(config)
    setLogRecordFactory(LogExtraFactory)
    requests_log = logging.getLogger("httpx")
    requests_log.addHandler(logging.NullHandler())
    requests_log.propagate = False


configure_logger()
