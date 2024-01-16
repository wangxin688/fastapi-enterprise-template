from typing import Any, ClassVar
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import DeclarativeBase

from src._types import VisibleName
from src.db._types import GUID


class Base(DeclarativeBase):
    __visible_name__: ClassVar[VisibleName] = {}
    __search_fields__: ClassVar[set[str]] = set()
    __i18n_files__: ClassVar[set[str]] = set()
    type_annotation_map: ClassVar = {UUID: GUID}

    def dict(self, exclude: set[str] | None = None, native_dict: bool = False) -> dict[str, Any]:
        """Return dict representation of model."""
        if not native_dict:
            return jsonable_encoder(self, exclude=exclude)
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name not in exclude}
