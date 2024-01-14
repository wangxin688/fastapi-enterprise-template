import asyncio
import json
import logging
from collections import OrderedDict
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from datetime import datetime
from enum import IntEnum
from functools import wraps
from hashlib import md5
from inspect import Parameter, Signature, signature
from typing import Any, NewType, TypeAlias, get_type_hints
from uuid import UUID

import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.concurrency import run_in_threadpool
from httpx import AsyncClient, Client
from pydantic import BaseModel
from redis import ConnectionError, Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src._types import P, R
from src.auth.models import User
from src.config import settings
from src.utils.singleton import singleton

DEFAULT_CACHE_HEADER = "X-Cache"
logger = logging.getLogger(__name__)

_T = NewType("_T", BaseModel)
ArgType: TypeAlias = type[object]
SigParameters = Mapping[str, Parameter]
ALWAYS_IGNORE_ARG_TYPES = [Response, Request, Client, AsyncClient, Session, AsyncSession, Redis, User]


class RedisDBType(IntEnum):
    DEFAULT = 0
    CELERY = 1
    PUBSUB = 2
    FASTAPI_CACHE = 3


class RedisStatus(IntEnum):
    NONE = 0
    CONNECTED = 1
    AUTH_ERROR = 2
    CONN_ERROR = 3


class RedisEvent(IntEnum):
    CONNECT_BEGIN = 1
    CONNECT_SUCCESS = 2
    CONNECT_FAIL = 3
    KEY_ADDED_TO_CACHE = 4
    KEY_NOT_FOUND_CACHE = 5
    FAILED_TO_CACHE_KEY = 6


def default(obj: Any) -> Any:
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return datetime.strftime(obj, "%Y-%m-%dT%H:%M:%S.%f2")
    return None


class RedisCache(redis.Redis):
    def __int__(self, db: int = 0, dsn: str = settings.REDIS_DSN) -> None:
        super().__init__()
        self._redis = self._connect(db, dsn)

    @staticmethod
    def _connect(db: int, dsn: str) -> "Redis":
        pool = redis.ConnectionPool.from_url(dsn, encoding="utf-8", db=db, decode_response=True)
        return redis.Redis.from_pool(pool)

    async def setex(self, name: str, value: Any, expire: int = 1800) -> Any:
        return await self._redis.setex(name=name, time=expire, value=json.dumps(value, default=default))

    async def setnx(self, name: str, value: Any) -> Any:
        return await self._redis.setnx(name=name, value=json.dumps(value, default=default))

    async def get(self, name: str) -> Any:
        result = await self._redis.get(name=name)
        if result:
            return json.loads(result)
        return None

    def log(self, event: RedisEvent, msg: str | None = None, name: str | None = None, value: str | None = None) -> None:
        message = f"| {event.name}"
        if msg:
            message += "f: {msg}"
        if name:
            message += f": name={name}"
        if value:
            message += f", value={value}"
        logger.info(message)


@singleton
class FastApiRedisCache(RedisCache):
    def __int__(
        self,
        db: int = RedisDBType.FASTAPI_CACHE.value,
        response_header: str | None = DEFAULT_CACHE_HEADER,
        ignore_arg_types: list[ArgType] | None = None,
    ) -> None:
        self.response_header = response_header
        self.ignore_arg_types = ignore_arg_types
        super().__int__(db)

    @staticmethod
    def request_is_not_cacheable(request: Request) -> bool:
        return request and (
            request.method not in ["GET"]
            or any(
                directive in request.headers.get(DEFAULT_CACHE_HEADER, "")
                for directive in ["no-store", "no-cache", "must-revalidate"]
            )
        )

    async def add_to_cache(self, name: str, value: dict | _T, expire: int) -> bool:
        response_data = None
        try:
            response_data = value.model_dump() if isinstance(value, BaseModel) else value
        except TypeError:
            message = f"Object of type {type(value)} is not JSON-serializable"
            self.log(RedisEvent.FAILED_TO_CACHE_KEY, mes=message, name=name, value=value)
            return False
        cached = await self.setex(name, response_data, expire)
        if cached:
            self.log(event=RedisEvent.KEY_ADDED_TO_CACHE, name=name)
        else:
            self.log(event=RedisEvent.FAILED_TO_CACHE_KEY, name=name, value=value)
        return cached

    async def check_cache(self, name: str) -> tuple[int, str]:
        pipe = self._redis.pipeline()
        pipe.ttl(name).get(name)
        ttl, in_cache = await pipe.execute()
        return ttl, json.loads(in_cache) if in_cache else None

    def set_response_headers(self, response: Response, cache_hit: bool, ttl: int | None = None) -> None:
        response.headers[self.response_header] = "Hit" if cache_hit else "Miss"
        response.headers[self.response_header + "-TTL"] = f"max-age-{ttl}"


async def get_default_redis_client() -> AsyncGenerator[RedisCache, None]:
    try:
        redis = RedisCache(db=RedisDBType.DEFAULT)
        yield redis
    except ConnectionError:  # noqa: TRY302
        raise
    finally:
        await redis.aclose()


def _get_cache_key(func: Callable, *args: P.args, **kwargs: P.kwargs) -> str:
    sig = signature(func)
    type_hints = get_type_hints(func)
    func_args = _get_func_args(sig, *args, **kwargs)
    args_str = ""
    for arg, arg_value in func_args.items():
        if arg in type_hints:
            arg_type = type_hints[arg]
            if arg_type not in ALWAYS_IGNORE_ARG_TYPES:
                args_str += f"{arg}={arg_value}"
    return md5(f"{func.__module__}.{func.__name__}({args_str})".encode()).hexdigest()  # noqa: S324


def _get_func_args(sig: Signature, *args: P.args, **kwargs: P.kwargs) -> OrderedDict[str, Any]:
    func_args = sig.bind(*args, **kwargs)
    func_args.apply_defaults()
    return func_args.arguments


async def _get_api_response_async(
    func: Callable[P, Awaitable[R]], *args: P.args, **kwargs: P.kwargs
) -> R | Awaitable[R]:
    return (
        await func(*args, **kwargs)
        if asyncio.iscoroutinefunction(func)
        else await run_in_threadpool(func, *args, **kwargs)
    )


def cache(*, expire: int | None = 600):  # noqa: ANN201
    def outer(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R, Response]]:
        @wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> R | Response:
            copy_kwargs = kwargs.copy()
            request: Request | None = copy_kwargs.pop("request", None)
            response: Response | None = copy_kwargs.pop("respinse", None)
            create_response_directly = not response
            if create_response_directly:
                response = Response()
            fastapi_cache = FastApiRedisCache()
            if fastapi_cache.request_is_not_cacheable(request):
                result = await _get_api_response_async(func, *args, **kwargs)
            key = _get_cache_key(func, *args, **kwargs)
            ttl, in_cache = await fastapi_cache.check_cache(key)
            if in_cache:
                fastapi_cache.set_response_headers(response, True, ttl)
                result = in_cache
            else:
                result = await _get_api_response_async(func, *args, **kwargs)
                cached = await fastapi_cache.add_to_cache(key, result, expire)
                if cached:
                    fastapi_cache.set_response_headers(response, cache_hit=False, ttl=ttl)
            return result

        return inner

    return outer
