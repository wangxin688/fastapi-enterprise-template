import logging
import sys
import traceback
from typing import NewType

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src._types import BaseResponse
from src.context import request_id_ctx
from src.errors import ERR_500
from src.i18n import _

_E = NewType("_E", Exception)
logger = logging.getLogger(__name__)


def log_exception(exc: _E | Exception, logger_trace_info: bool) -> None:
    ex_type, _tmp, ex_traceback = sys.exc_info
    trace_back = traceback.format_list(traceback.extract_tb(ex_traceback)[-1:])[-1]
    logger.warning("ErrorMessage: %s" % str(exc))
    logger.warning("Exception Type %s: " % ex_type.__name__)
    if not logger_trace_info:
        logger.warning("Stack trace: %s" % trace_back)
    else:
        logger.exception("Stace trace: %s" % trace_back)


def default_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log_exception(exc, logger_trace_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=BaseResponse(
            code=ERR_500.code, data=jsonable_encoder(str(exc)), message=_(ERR_500.message, request_id_ctx.get())
        ),
    )


exception_handlers = []
