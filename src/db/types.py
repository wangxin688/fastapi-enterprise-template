import uuid
from datetime import date, datetime
from typing import Annotated, Any

from sqlalchemy import CHAR, Boolean, Date, DateTime, Dialect, String, func, type_coerce
from sqlalchemy.dialects.postgresql import BYTEA, UUID
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import expression
from sqlalchemy.sql.elements import BindParameter, ColumnElement
from sqlalchemy.types import TypeDecorator, TypeEngine

from src.conf import settings


class EncryptedString(TypeDecorator):
    impl = BYTEA
    cache_ok = True

    def __init__(self, secret_key: str | None = settings.SECRET_KEY) -> None:
        super().__init__()
        self.secret = secret_key

    def bind_expression(self, bind_value: BindParameter) -> ColumnElement | None:
        bind_value = type_coerce(bind_value, String)
        return func.pgp_sym_encrypt(bind_value, self.secret)

    def column_expression(self, column: ColumnElement) -> ColumnElement | None:
        return func.pgp_sym_decrypt(column, self.secret)


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type or MSSQL's UNIQUEIDENTIFIER,
    otherwise uses CHAR(32), storing as stringified hex values.

    """

    impl = CHAR
    cache_ok = True

    _default_type = CHAR(32)

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[UUID] | TypeEngine[str]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())
        return dialect.type_descriptor(self._default_type)

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return self._uuid_as_str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> UUID | None:  # noqa: ARG002
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value


uuid_pk = Annotated[uuid.UUID, mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)]
bool_true = Annotated[bool, mapped_column(Boolean, server_default=expression.true())]
bool_false = Annotated[bool, mapped_column(Boolean, server_default=expression.false())]
datetime_required = Annotated[datetime, mapped_column(DateTime(timezone=True))]
datetime_required = Annotated[datetime, mapped_column(DateTime(timezone=True))]
date_required = Annotated[date, mapped_column(Date)]
date_optional = Annotated[date | None, mapped_column(Date)]
