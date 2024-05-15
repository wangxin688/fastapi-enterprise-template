from typing import TYPE_CHECKING

from sqlalchemy import Integer, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.types import DateTimeTZ
from src.core.utils.context import user_ctx

if TYPE_CHECKING:
    from datetime import datetime

    from src.features.auth.models import User


class AuditUserMixin:
    created_at: Mapped["datetime"] = mapped_column(DateTimeTZ, default=func.now(), index=True)
    updated_at: Mapped["datetime"] = mapped_column(DateTimeTZ, default=func.now(), onupdate=func.now())

    @declared_attr
    @classmethod
    def created_by_fk(cls) -> Mapped[int | None]:
        return mapped_column(Integer, default=user_ctx.get)

    @declared_attr
    @classmethod
    def updated_by_fk(cls) -> Mapped[int | None]:
        return mapped_column(Integer, default=user_ctx.get, nullable=True)

    @declared_attr
    @classmethod
    def created_by(cls) -> Mapped["User"]:
        return relationship(
            "User",
            foreign_keys=[cls.created_by_fk],
            primaryjoin=f"{cls.__name__}.created_by_fk==User.id",
            enable_typechecks=False,
            uselist=False,
        )

    @declared_attr
    @classmethod
    def updated_by(cls) -> Mapped["User"]:
        return relationship(
            "User",
            foreign_keys=[cls.updated_by_fk],
            primaryjoin=f"{cls.__name__}.updated_by_fk==User.id",
            enable_typechecks=False,
            uselist=False,
        )
