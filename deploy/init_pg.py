import asyncio

from sqlalchemy import text

from src.db.session import async_session

async def create_pg_extensions() -> None:
    async with async_session() as session:
        await session.execute(text('create EXTENSION if not EXISTS "pgcrypto"'))
        await session.execute(text('create EXTENSION if not EXISTS "hstore"'))
        await session.commit()

if __name__ == "__main__":
    asyncio.run(create_pg_extensions())
    

