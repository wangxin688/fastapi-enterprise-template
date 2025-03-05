import asyncio
import gc
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.core.config import settings
from src.core.database.session import async_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    loop.set_debug(True)
    yield loop
    gc.collect()
    loop.close()


@pytest.fixture(scope="session")
async def session() -> AsyncGenerator["AsyncSession", None]:
    async with async_session() as session:
        yield session


@pytest.fixture(scope="session")
async def admin_token() -> dict[str, str]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=settings.BASE_URL) as client:
        response = await client.post(
            "/api/v1/admin/pwd-login", data={"username": "admin@system.com", "password": "admin"}
        )
        return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
async def client(admin_token: dict[str, str]) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=settings.BASE_URL, headers=admin_token) as client:
        yield client
