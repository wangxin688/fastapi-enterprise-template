import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Group, Role, User
from src.core.database.session import async_session
from src.features.auth.consts import ReservedRoleSlug


async def create_pg_extensions(session: AsyncSession) -> None:
    await session.execute(text('create EXTENSION if not EXISTS "pgcrypto"'))
    await session.execute(text('create EXTENSION if not EXISTS "hstore"'))
    await session.commit()


async def create_init_user(session: AsyncSession) -> None:
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


async def init_app() -> None:
    async with async_session() as session:
        await create_pg_extensions(session)
        await create_init_user(session)


if __name__ == "__main__":
    asyncio.run(init_app())
