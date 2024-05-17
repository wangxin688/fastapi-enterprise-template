from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from src.core.utils._serialization import json_dumps, json_loads
from src.core.utils.dataclass import Empty, EmptyType

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import IsolationLevel
    from sqlalchemy.pool import Pool

__all__ = ("EngineConfig",)

type _EchoFlagType = "None | bool | Literal['debug']"


class EngineConfig(BaseModel):
    """Sqlalchemy engine configuration.
    see details: https://docs.sqlalchemy.org/en/20/core/engines.html
    """

    connect_args: dict[Any, Any] | EmptyType = Field(
        default=Empty,
        description="""A dictionary of arguments which will be passed directly
        to the DBAPI's ``connect()`` method as keyword arguments""",
    )

    echo: _EchoFlagType | EmptyType = Field(
        default=Empty,
        description="""If ``True``, the Engine will log all statements as well as a ``repr()`` of their parameter lists
        to the defaultlog handler, which defaults to ``sys.stdout`` for output. If set to the string "debug", result
        rows will be printed to the standard output as well. The echo attribute of Engine can be modified at any time
        to turn logging on and off; direct control of logging is also available using the standard Python logging module
    """,
    )

    echo_pool: _EchoFlagType | EmptyType = Empty

    isolation_level: "IsolationLevel| EmptyType" = Field(
        default=Empty,
        description="""Optional string name of an isolation level which will be set on all new connections
        unconditionally Isolation levels are typically some subset of the string names "SERIALIZABLE",
        "REPEATABLE READ", "READ COMMITTED", "READ UNCOMMITTED" and "AUTOCOMMIT" based on backend.""",
    )

    json_serializer: Callable[[str], Any] = json_dumps

    json_deserializer: Callable[[Any], str] = json_loads

    max_over_flow: int | EmptyType = Field(
        default=Empty,
        description="""The number of connections to allow in connection pool “overflow”,
        that is connections that can be opened above and beyond the pool_size setting,
        which defaults to five. This is only used with:class:`QueuePool <sqlalchemy.pool.QueuePool>`.""",
    )

    pool_size: int | EmptyType = Field(
        default=Empty,
        description="""The number of connections to keep open inside the connection pool. This used with
    :class:`QueuePool <sqlalchemy.pool.QueuePool>` as well as
    :class:`SingletonThreadPool <sqlalchemy.pool.SingletonThreadPool>`. With
    :class:`QueuePool <sqlalchemy.pool.QueuePool>`, a pool_size setting of ``0`` indicates no limit; to disable pooling,
    set ``poolclass`` to :class:`NullPool <sqlalchemy.pool.NullPool>` instead.""",
    )

    pool_recycle: int | EmptyType = Field(
        default=Empty,
        description="""This setting causes the pool to recycle connections after the given number of seconds has passed.
        It defaults to``-1``, or no timeout. For example, setting to ``3600`` means connections will be recycled after
        one hour. Note that MySQL in particular will disconnect automatically if no activity is detected on a connection
        for eight hours (although this is configurable with the MySQLDB connection itself and the server configuration
        as well).""",
    )

    pool_use_lifo: bool | EmptyType = Field(
        default=Empty,
        description="""Use LIFO (last-in-first-out) when retrieving connections from :class:`QueuePool <sqlalchemy.pool.
        QueuePool>` instead of FIFO (first-in-first-out). Using LIFO, a server-side timeout scheme can reduce the number
        of connections used during non-peak periods of use. When planning for server-side timeouts, ensure that a
        recycle or pre-ping strategy is in use to gracefully handle stale connections.""",
    )

    pool_pre_ping: bool | EmptyType = Field(
        default=Empty,
        description="""If True will enable the connection pool “pre-ping” feature that tests connections for liveness
        upon eachcheckout.""",
    )

    pool_timeout: int | EmptyType = Field(
        default=Empty,
        description="""Number of seconds to wait before giving up on getting a connection from the pool.
        This is only used with :class:`QueuePool <sqlalchemy.pool.QueuePool>`. This can be a float but
        is subject to the limitations of Python time functions which may not be reliable in the tens of milliseconds.
        """,
    )

    pool: "Pool| EmptyType" = Field(
        default=Empty,
        description="""An already-constructed instance of :class:`Pool <sqlalchemy.pool.Pool>`, such as a
    :class:`QueuePool <sqlalchemy.pool.QueuePool>` instance. If non-None, this pool will be used directly as the
    underlying connection pool for the engine, bypassing whatever connection parameters are present in the URL argument.
    For information on constructing connection pools manually, see
    `Connection Pooling <https://docs.sqlalchemy.org/en/20/core/pooling.html>`_.""",
    )

    poolclass: "type[Pool]| EmptyType" = Field(
        default=Empty,
        description="""A :class:`Pool <sqlalchemy.pool.Pool>` subclass, which will be used to create a connection pool
        instance using the connection parameters given in the URL. Note this differs from pool in that you don`t
        actually instantiate the pool in this case, you just indicate what type of pool to be used.""",
    )

    query_cache_size: int | EmptyType = Field(
        default=Empty,
        description="""Size of the cache used to cache the SQL string form of queries. Set to zero to disable caching.

    See :attr:`query_cache_size <sqlalchemy.get_engine.params.query_cache_size>` for more info.
    """,
    )

    pool_reset_on_return: Literal["reset", "rollback", "commit"] | EmptyType = Empty
