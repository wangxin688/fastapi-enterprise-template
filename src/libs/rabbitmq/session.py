import json
import logging
from dataclasses import dataclass

from aio_pika import Message, connect_robust
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection

logger = logging.getLogger(__name__)


@dataclass
class RabbitMQSession:
    connection: AbstractRobustConnection | None = None
    channel: AbstractRobustChannel | None = None

    @property
    async def _is_open(self) -> bool:
        """Check if the session is open."""
        return (
            self.connection is not None
            and not self.connection.is_closed
            and self.channel is not None
            and not self.channel.is_closed
        )

    async def _close(self) -> None:
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

        self.connection = None
        self.channel = None

    async def connect(self, ampq_url: str, publisher_confirms: bool) -> None:
        if self._is_open:
            return
        try:
            self.connection = await connect_robust(url=ampq_url)
            self.channel = await self.connection.channel(publisher_confirms=publisher_confirms)  # type: ignore  # noqa: PGH003
            logger.info("Connected to RabbitMQ successfully.")
        except Exception:
            await self._close()
            logger.exception("Failed to connect to RabbitMQ.")
            raise

    async def disconnect(self) -> None:
        if not self._is_open:
            return
        await self._close()

    async def publish(self, message: Message | dict, routing_key: str, expiration: int | None = None) -> None:
        if not self.channel or self.channel.is_closed:
            raise RuntimeError("RabbitMQ channel is not open.")
        if not isinstance(message, Message):
            message = Message(body=json.dumps(message, default=str).encode(), expiration=expiration)
        async with self.channel.transaction():
            await self.channel.default_exchange.publish(message, routing_key)


mq = RabbitMQSession()
