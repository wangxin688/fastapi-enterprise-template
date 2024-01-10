from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_pg_extensions(session: AsyncSession) -> None:
    await session.execute(text('create EXTENSION if not EXISTS "pgcrypto"'))
    await session.execute(text('create EXTENSION if not EXISTS "hstore"'))
    await session.commit()
