from typing import Any, ClassVar, TypeVar

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import DeclarativeBase

from src.core._types import VisibleName


class Base(DeclarativeBase):
    __visible_name__: ClassVar[VisibleName] = {"en_US": "base", "zh_CN": "base"}
    __search_fields__: ClassVar[set[str]] = set()
    __i18n_fields__: ClassVar[set[str]] = set()

    def dict(self, exclude: set[str] | None = None, native_dict: bool = False) -> dict[str, Any]:
        """Return dict representation of model."""
        if not native_dict:
            return jsonable_encoder(self, exclude=exclude)
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name not in exclude}

    def __getattribute__(self, name: str) -> Any:
        return super().__getattribute__(name)


ModelT = TypeVar("ModelT", bound=Base)
