from typing import TYPE_CHECKING

from fastapi.encoders import jsonable_encoder
from sqlalchemy import JSON, ForeignKey, Integer, String, event, func, insert, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, Mapper, class_mapper, mapped_column, relationship
from sqlalchemy.orm.attributes import get_history

from src.core.database.types import DateTimeTZ, int_pk
from src.core.models.base import Base
from src.core.utils.context import orm_diff_ctx, request_id_ctx, user_ctx

if TYPE_CHECKING:
    from datetime import datetime

    from src.core.models.base import ModelT
    from src.features.auth.models import User


def get_object_change(obj: Mapper) -> dict:
    insp = inspect(obj)
    changes: dict[str, dict] = {
        "post_change": {},
        "diff": {},
    }
    for attr in class_mapper(obj.__class__).column_attrs:
        before = None
        after = None
        if getattr(insp.attrs, attr.key).hisotry.has_changes():
            if get_history(obj, attr.key)[2]:
                before = get_history(obj, attr.key)[2].pop()
                after = getattr(obj, attr.key)
            elif get_history(obj, attr.key)[0]:
                before = get_history(obj, attr.key)[0]
                after = getattr(obj, attr.key)
            if before != after:
                changes["diff"][attr.key] = {"before": before, "after": after}
    return jsonable_encoder(changes, exclude={"children", "parent"})


class AuditLog:
    id: Mapped[int_pk]
    created_at: Mapped["datetime"] = mapped_column(DateTimeTZ, default=func.now())
    request_id: Mapped[str]
    action: Mapped[str] = mapped_column(String, nullable=False)
    diff: Mapped[dict | None] = mapped_column(JSON)

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
    def audit_log(cls: type["ModelT"]) -> Mapped[list["AuditLog"]]:
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
    def log_create(cls, mapper: Mapper, connection: Connection, target: "ModelT") -> None:  # noqa: ARG003
        connection.execute(
            insert(cls.AuditLog),
            {
                "request_id": request_id_ctx.get(),
                "action": "create",
                "diff": target.dict(native_dict=True),
                "parent_id": target.id,
                "user_id": user_ctx.get(),
            },
        )

    @classmethod
    def log_update(cls, mapper: Mapper, connection: Connection, target: "ModelT") -> None:  # noqa: ARG003
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
    def log_delete(cls, mapper: Mapper, connection: Connection, target: "ModelT") -> None:  # noqa: ARG003
        connection.execute(
            insert(cls.AuditLog),
            {
                "request_id": request_id_ctx.get(),
                "action": "delete",
                "diff": target.dict(native_dict=True),
                "parent_id": target.id,
                "user_id": user_ctx.get(),
            },
        )

    @classmethod
    def __declare_last__(cls) -> None:
        event.listen(cls, "after_insert", cls.log_create, propagate=True)
        event.listen(cls, "after_update", cls.log_update, propagate=True)
        event.listen(cls, "after_delete", cls.log_delete, propagate=True)
