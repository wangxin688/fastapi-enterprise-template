from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioreids
import sentry_sdk
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware

from src.core.config import _Env, settings
from src.core.errors.auth_exceptions import default_exception_handler, exception_handlers, sentry_ignore_errors
from src.libs.redis import cache
from src.openapi import openapi_description
from src.register.middlewares import RequestMiddleware
from src.register.routers import router


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
        pool = aioreids.ConnectionPool.from_url(
            settings.REDIS_DSN, encoding="utf-8", db=cache.RedisDBType.DEFAULT, decode_response=True
        )
        cache.redis_client = cache.FastapiCache(connection_pool=pool)
        yield
        await pool.disconnect()

    if _Env.PROD.name == settings.ENV:
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
        lifespan=lifespan,
    )
    app.include_router(router, prefix="/api")
    for handler in exception_handlers:
        app.add_exception_handler(exc_class_or_status_code=handler["exception"], handler=handler["handler"])
    app.add_middleware(RequestMiddleware)
    app.add_middleware(ServerErrorMiddleware, handler=default_exception_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()
