from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from src.context import tenant_ctx
from src.db._types import GUID


class Base(DeclarativeBase):
    __multi_tenant__: bool = True
    __search_fields__: ClassVar = set()
    type_annotation_map: ClassVar = {UUID: GUID}

    @declared_attr
    @classmethod
    def tenant_id(cls) -> Mapped[UUID]:
        if not cls.__multi_tenant__:
            return None
        return mapped_column(UUID, ForeignKey("tenant.id", ondelete="CASCADE"), index=True, default=tenant_ctx.get)
