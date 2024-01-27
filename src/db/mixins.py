from datetime import datetime
from typing import TYPE_CHECKING

from fastapi.encoders import jsonable_encoder
from sqlalchemy import DateTime, ForeignKey, Integer, String, event, func, insert, inspect
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.engine import Connection
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, Mapper, class_mapper, mapped_column, relationship
from sqlalchemy.orm.attributes import get_history

from src.context import orm_diff_ctx, request_id_ctx, user_ctx
from src.db._types import int_pk
from src.db.base import Base

if TYPE_CHECKING:
    from src.auth.models import User


class AuditTimeMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


def get_object_change(obj: Mapper) -> dict:
    insp = inspect(obj)
    changes: dict[str, dict] = {
        "post_change": {},
        "diff": {},
    }
    for attr in class_mapper(obj.__class__).column_attrs:
        if getattr(insp.attrs, attr.key).hisotry.has_changes():
            if get_history(obj, attr.key)[2]:
                before = get_history(obj, attr.key)[2].pop()
                after = getattr(obj, attr.key)
            elif get_history(obj, attr.key)[0]:
                before = get_history(obj, attr.key)[0]
                after = getattr(obj, attr.key)
            if before != after:
                changes["diff"][attr.key] = {"before": before, "after": after}
    return jsonable_encoder(changes)


class AuditLog:
    id: Mapped[int_pk]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    request_id: Mapped[str]
    action: Mapped[str] = mapped_column(String, nullable=False)
    diff: Mapped[dict | None] = mapped_column(JSON)
    post_change: Mapped[dict | None] = mapped_column(JSON)

    @declared_attr
    @classmethod
    def user_id(cls) -> Mapped[int | None]:
        return mapped_column(
            Integer,
            ForeignKey("user.id", ondelete="SET NULL"),
            default=user_ctx.get,
            nullable=True,
        )

    @declared_attr
    @classmethod
    def user(cls) -> Mapped["User"]:
        return relationship("User", lazy="selectin")


class AuditLogMixin:
    @declared_attr
    @classmethod
    def audit_log(cls) -> Mapped[list["AuditLog"]]:
        cls.AuditLog = type(
            f"{cls.__name__}AuditLog",
            (AuditLog, Base),
            {
                "__tablename__": f"{cls.__tablename__}_audit_log",
                "parent_id": mapped_column(
                    Integer,
                    ForeignKey(f"{cls.__tablename__}.id", ondelete="SET NULL"),
                    nullable=True,
                ),
                "audit_log": relationship(cls, viewonly=True),
            },
        )
        return relationship(cls.AuditLog)

    @classmethod
    def log_create(cls, mapper: Mapper, connection: Connection, target: Mapper) -> None:  # noqa: ARG003
        connection.execute(
            insert(cls.AuditLog),
            {
                "request_id": request_id_ctx.get(),
                "action": "create",
                "post_change": target.dict(exclude_relationship=True),
                "parent_id": target.id,
                "user_id": user_ctx.get(),
            },
        )

    @classmethod
    def log_update(cls, mapper: Mapper, connection: Connection, target: Mapper) -> None:  # noqa: ARG003
        changes = get_object_change(target)
        if changes is not None:
            orm_diff_ctx.set(changes)
            connection.execute(
                insert(cls.AuditLog),
                {
                    "request_id": request_id_ctx.get(),
                    "action": "update",
                    "diff": changes["diff"],
                    "parent_id": target.id,
                    "user_id": user_ctx.get(),
                },
            )

    @classmethod
    def log_delete(cls, mapper: Mapper, connection: Connection, target: Mapper) -> None:  # noqa: ARG003
        connection.execute(
            insert(cls.AuditLog),
            {
                "request_id": request_id_ctx.get(),
                "action": "delete",
                "diff": target.dict(exclude_relationship=True),
                "parent_id": target.id,
                "user_id": user_ctx.get(),
            },
        )

    @classmethod
    def __declare_last__(cls) -> None:
        event.listen(cls, "after_insert", cls.log_create, propagate=True)
        event.listen(cls, "after_update", cls.log_update, propagate=True)
        event.listen(cls, "after_delete", cls.log_delete, propagate=True)


class AuditUserMixin:
    @declared_attr
    @classmethod
    def created_by_fk(cls) -> Mapped[int | None]:
        return mapped_column(Integer, ForeignKey("user.id"), default=user_ctx.get, nullable=True)

    @declared_attr
    @classmethod
    def updated_by_fk(cls) -> Mapped[int | None]:
        return mapped_column(Integer, ForeignKey("user.id"), default=user_ctx.get, nullable=True)

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
