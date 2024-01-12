from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware

from src.config import settings
from src.enums import Env
from src.exception_handlers import default_exception_handler, exception_handlers
from src.exceptions import sentry_ignore_errors
from src.middlewares import RequestMiddleware
from src.openapi import openapi_description
from src.routers import router


def create_app() -> FastAPI:
    @asynccontextmanager
    def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
        ...

    if settings.ENV == Env.PRD.name:  # noqa: SIM300
        sentry_sdk.init(
            dsn=settings.WEB_SENTRY_DSN,
            sample_rate=settings.SENTRY_SAMPLE_RATE,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            release=settings.VERSION,
            send_default_pii=True,
            ignore_errors=sentry_ignore_errors,
        )
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        summary=settings.DESCRIPTION,
        description=openapi_description,
        docs_url=None,
        redoc_url=None,
        swagger_ui_init_oauth={},
        lifespan=lifespan,
    )
    app.include_router(router, prefix="/api")
    for handler in exception_handlers:
        app.add_exception_handler(exc_class_or_status_code=handler["name"], handler=handler[handler])
    app.add_middleware(RequestMiddleware)
    app.add_middleware(ServerErrorMiddleware, handler=default_exception_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS,
        allow_credentials=True,
        all_methods=settings.BACKEND_CORS,
        allow_headers=settings.BACKEND_CORS,
    )
    return app
