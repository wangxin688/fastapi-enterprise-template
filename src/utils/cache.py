import asyncio
import json
import logging
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
from enum import IntEnum
from functools import partial, update_wrapper, wraps
from hashlib import md5
from inspect import Parameter, Signature, signature
from typing import Any, NewType, TypeAlias, get_type_hints
from uuid import UUID

import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.concurrency import run_in_threadpool
from httpx import AsyncClient, Client
from pydantic import BaseModel
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src._types import AppStrEnum, P, R
from src.auth.models import User

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


class CacheNamespace(AppStrEnum):
    API_CACHE = "api_"
    NORMAL_CACHE = "nc_"


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


class FastapiCache(redis.Redis):
    response_header: str = DEFAULT_CACHE_HEADER
    ignore_arg_types: list[ArgType] = ALWAYS_IGNORE_ARG_TYPES

    async def set_ex(self, name: str, value: Any, expire: int = 1800, namespace: CacheNamespace | None = None) -> Any:
        return self.setex(name=namespace + name, time=expire, value=json.dumps(value))

    async def set_nx(self, name: str, value: Any, namespace: CacheNamespace | None = None) -> Any:
        return await self.setnx(name=namespace + name, value=json.dumps(value, default=default))

    async def get_cache(self, name: str, namespace: CacheNamespace | None = None) -> Any:
        result = await self.get(name=namespace + name)
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
        cached = await self.setex(name, response_data, expire, CacheNamespace.API_CACHE)
        if cached:
            self.log(event=RedisEvent.KEY_ADDED_TO_CACHE, name=name)
        else:
            self.log(event=RedisEvent.FAILED_TO_CACHE_KEY, name=name, value=value)
        return cached

    async def check_cache(self, name: str) -> tuple[int, str]:
        pipe = self._redis.pipeline()
        pipe.ttl(CacheNamespace.API_CACHE + name).get(CacheNamespace.API_CACHE + name)
        ttl, in_cache = await pipe.execute()
        return ttl, json.loads(in_cache) if in_cache else None

    def set_response_headers(self, response: Response, cache_hit: bool, ttl: int | None = None) -> None:
        response.headers[self.response_header] = "Hit" if cache_hit else "Miss"
        response.headers[self.response_header + "-TTL"] = f"max-age-{ttl}"


redis_client: FastapiCache = None


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
            if redis_client.request_is_not_cacheable(request):
                result = await _get_api_response_async(func, *args, **kwargs)
            key = _get_cache_key(func, *args, **kwargs)
            ttl, in_cache = await redis_client.check_cache(key)
            if in_cache:
                redis_client.set_response_headers(response, True, ttl)
                result = in_cache
            else:
                result = await _get_api_response_async(func, *args, **kwargs)
                cached = await redis_client.add_to_cache(key, result, expire)
                if cached:
                    redis_client.set_response_headers(response, cache_hit=False, ttl=ttl)
            return result

        return inner

    return outer


cache_one_hour = partial(cache, expire=3600)
cache_one_day = partial(cache, expire=86400)

update_wrapper(cache_one_day, cache)
update_wrapper(cache_one_hour, cache)
