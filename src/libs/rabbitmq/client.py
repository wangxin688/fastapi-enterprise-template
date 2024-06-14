from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from httpx import AsyncClient, Response


class RabbitMQClient:
    headers: ClassVar[dict[str, str]] = {"content-type": "application/json"}

    def __init__(self, url: str, username: str, password: str) -> None:
        self.url: str = url
        self.auth: tuple[str, str] = (username, password)

    async def create_vhost(self, client: "AsyncClient", vhost: str) -> "Response":
        return await client.put(f"{self.url}/api/vhosts/{vhost}", auth=self.auth, headers=self.headers)

    async def delete_vhost(self, client: "AsyncClient", vhost: str) -> "Response":
        return await client.delete(f"{self.url}/api/vhosts/{vhost}", auth=self.auth, headers=self.headers)

    async def get_vhosts(self, client: "AsyncClient") -> "Response":
        return await client.get(f"{self.url}/api/vhosts", auth=self.auth, headers=self.headers)

    async def get_users(self, client: "AsyncClient") -> "Response":
        return await client.get(f"{self.url}/api/users", auth=self.auth, headers=self.headers)

    async def create_user(self, client: "AsyncClient", username: str, password: str, tags: str = "") -> "Response":
        return await client.put(
            f"{self.url}/api/users/{username}",
            auth=self.auth,
            headers=self.headers,
            json={"username": username, "password": password, "tags": tags},
        )

    async def delete_user(self, client: "AsyncClient", username: str) -> "Response":
        return await client.delete(f"{self.url}/api/users/{username}", auth=self.auth, headers=self.headers)

    async def create_vhost_permission(
        self, client: "AsyncClient", vhost: str, username: str, configure: str, write: str, read: str
    ) -> "Response":
        return await client.put(
            f"{self.url}/api/permissions/{vhost}/{username}",
            auth=self.auth,
            headers=self.headers,
            json={"configure": configure, "write": write, "read": read, "username": username, "vhost": vhost},
        )
