from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect


class DateTimeTZ(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    @property
    def python_type(self) -> type[datetime]:
        return datetime

    def process_bind_param(self, value: datetime | None, dialect: "Dialect") -> datetime | None:  # noqa: ARG002
        if value is None:
            return value
        if not value.tzinfo:
            msg = "tzinfo is required"
            raise TypeError(msg)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: "Dialect") -> datetime | None:  # noqa: ARG002
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
