import asyncio

from sqlalchemy import text

from src.auth.models import Group, Role, User
from src.db.session import async_session
from src.enums import ReservedRoleSlug


async def create_pg_extensions() -> None:
    async with async_session() as session:
        await session.execute(text('create EXTENSION if not EXISTS "pgcrypto"'))
        await session.execute(text('create EXTENSION if not EXISTS "hstore"'))
        await session.commit()


async def create_init_user() -> None:
    async with async_session() as session:
        new_role = Role(name="Administrator", slug=ReservedRoleSlug.ADMIN, description="App system admin")
        session.add(new_role)
        await session.commit()
        new_group = Group(
            name="System Administrator",
            description="App systemic administrators group",
            role_id=new_role.id,
            user=[
                User(
                    name="Administrator",
                    email="admin@system.com",
                    password="admin",  # noqa: S106
                    role_id=new_role.id,
                )
            ],
        )
        session.add(new_group)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(create_pg_extensions())
    asyncio.run(create_init_user())
