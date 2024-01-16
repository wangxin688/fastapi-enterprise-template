import logging
import sys
import traceback
from typing import NewType

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src import errors, exceptions
from src.context import request_id_ctx
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


async def token_invalid_handler(request: Request, exc: exceptions.TokenInvalidError) -> JSONResponse:
    log_exception(exc, False)
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=errors.ERR_10002.dict())


async def invalid_token_for_refresh_handler(
    request: Request, exc: exceptions.TokenInvalidForRefreshError
) -> JSONResponse:
    log_exception(exc, False)
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=errors.ERR_10004.dict())


async def token_expired_handler(request: Request, exc: exceptions.TokenExpireError) -> JSONResponse:
    log_exception(exc, False)
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=errors.ERR_10003.dict())


async def permission_deny_handler(request: Request, exc: exceptions.PermissionDenyError) -> JSONResponse:
    log_exception(exc, False)
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=errors.ERR_10004.dict())


async def resource_not_found_handler(request: Request, exc: exceptions.NotFoundError) -> JSONResponse:
    log_exception(exc, True)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": errors.ERR_404.error,
            "message": _(errors.ERR_404.message, name=exc.name, filed=exc.field, value=exc.value),
        },
    )


async def resource_exist_handler(request: Request, exc: exceptions.ExistError) -> JSONResponse:
    log_exception(exc, True)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": errors.ERR_409.error,
            "message": _(errors.ERR_409.message, name=exc.name, filed=exc.field, value=exc.value),
        },
    )


def gener_error_handler(request: Request, exc: exceptions.GenerError) -> JSONResponse:
    log_exception(exc, True)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error.error,
            "message": _(exc.error.message, **exc.params),
        },
    )


def default_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log_exception(exc, logger_trace_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": errors.ERR_500.error, "message": _(errors.ERR_500.message, request_id=request_id_ctx.get())},
    )


exception_handlers = [
    {"exception": exceptions.TokenInvalidError, "handler": token_invalid_handler},
    {"exception": exceptions.TokenExpireError, "handler": token_expired_handler},
    {"exception": exceptions.TokenInvalidForRefreshError, "handler": invalid_token_for_refresh_handler},
    {"exception": exceptions.PermissionDenyError, "handler": permission_deny_handler},
    {"exception": exceptions.NotFoundError, "handler": resource_not_found_handler},
    {"exception": exceptions.ExistError, "handler": resource_exist_handler},
    {"exception": exceptions.GenerError, "handler": gener_error_handler},
]
