from typing import TYPE_CHECKING

from fastapi import status

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_main(client: "AsyncClient") -> None:
    response = await client.get("/docs")
    assert response.status_code == status.HTTP_200_OK
