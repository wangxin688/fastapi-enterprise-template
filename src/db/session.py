import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
    url=settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    future=True,
    connection_args={"server_settings": {"jit": "off"}},
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_POOL_MAX_OVERFLOW,
)
async_session = async_sessionmaker(async_engine, autoflush=False, expires_on_commit=False)
