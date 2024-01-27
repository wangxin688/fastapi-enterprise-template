import uuid
from datetime import date, datetime
from enum import IntEnum
from typing import Annotated, TypeVar, no_type_check

from sqlalchemy import Boolean, Date, DateTime, Integer, String, func, type_coerce
from sqlalchemy.dialects.postgresql import BYTEA, UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import expression
from sqlalchemy.sql.elements import BindParameter, ColumnElement
from sqlalchemy.types import TypeDecorator

from src.config import settings

T = TypeVar("T", bound=IntEnum)


class EncryptedString(TypeDecorator):
    impl = BYTEA
    cache_ok = True

    def __init__(self, secret_key: str | None = settings.SECRET_KEY) -> None:
        super().__init__()
        self.secret = secret_key

    @no_type_check
    def bind_expression(self, bind_value: BindParameter) -> ColumnElement | None:
        bind_value = type_coerce(bind_value, String)  # type: ignore  # noqa: PGH003
        return func.pgp_sym_encrypt(bind_value, self.secret)

    @no_type_check
    def column_expression(self, column: ColumnElement) -> ColumnElement | None:
        return func.pgp_sym_decrypt(column, self.secret)


class IntegerEnum(TypeDecorator):
    impl = Integer
    cache_ok = True

    def __init__(self, enum_type: type[T]) -> None:
        super().__init__()
        self.enum_type = enum_type

    @no_type_check
    def process_bind_param(self, value: int, dialect: Dialect) -> int:  # noqa: ARG002
        if isinstance(value, self.enum_type):
            return value.value
        msg = f"expected {self.enum_type.__name__} value, got {value.__class__.__name__}"
        raise ValueError(msg)

    @no_type_check
    def process_result_value(self, value: int, dialect: Dialect):  # noqa: ANN202, ARG002
        return self.enum_type(value)

    @no_type_check
    def copy(self, **kwargs):  # noqa: ANN202, ARG002, ANN003
        return IntegerEnum(self.enum_type)


uuid_pk = Annotated[uuid.UUID, mapped_column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)]
int_pk = Annotated[int, mapped_column(Integer, primary_key=True)]
bool_true = Annotated[bool, mapped_column(Boolean, server_default=expression.true())]
bool_false = Annotated[bool, mapped_column(Boolean, server_default=expression.false())]
datetime_required = Annotated[datetime, mapped_column(DateTime(timezone=True))]
datetime_required = Annotated[datetime, mapped_column(DateTime(timezone=True))]
date_required = Annotated[date, mapped_column(Date)]
date_optional = Annotated[date | None, mapped_column(Date)]
