from enum import IntEnum
from typing import TYPE_CHECKING, Any, TypeVar, no_type_check

from sqlalchemy import Integer
from sqlalchemy.types import TypeDecorator

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect

T = TypeVar("T", bound=IntEnum)


class IntegerEnum(TypeDecorator[T]):
    impl = Integer
    cache_ok = True

    def __init__(self, enum_type: type[T]) -> None:
        super().__init__()
        self.enum_type = enum_type

    @no_type_check
    def process_bind_param(self, value: int, dialect: "Dialect") -> int:  # noqa: ARG002
        if isinstance(value, self.enum_type):
            return value.value
        msg = f"expected {self.enum_type.__name__} value, got {value.__class__.__name__}"
        raise ValueError(msg)

    @no_type_check
    def process_result_value(self, value: int, dialect: "Dialect") -> "T":  # noqa: ARG002
        return self.enum_type(value)

    @no_type_check
    def copy(self, **kwargs: Any) -> "IntegerEnum[T]":  # noqa: ARG002
        return IntegerEnum(self.enum_type)
