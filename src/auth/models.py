from datetime import datetime
from typing import ClassVar
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, and_, func, select
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from src.db import _types
from src.db.base import Base
from src.db.mixins import AuditTimeMixin


class RolePermission(Base):
    __tablename__ = "role_permission"
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey("permission.id"), primary_key=True)


class Role(Base, AuditTimeMixin):
    __tablename__ = "role"
    __search_fields__: ClassVar = {"name"}
    __visible_name__ = {"en_US": "Role", "zh_CN": "用户角色"}
    id: Mapped[_types.int_pk]
    name: Mapped[str]
    slug: Mapped[str]
    description: Mapped[str | None]
    permission: Mapped[list["Permission"]] = relationship(secondary="role_permission", backref="role")


class Permission(Base):
    __tablename__ = "permission"
    __visible_name__ = {"en_US": "Permission", "zh_CN": "权限"}
    id: Mapped[_types.uuid_pk]
    name: Mapped[str]
    url: Mapped[str]
    method: Mapped[str]
    tag: Mapped[str]


class Group(Base, AuditTimeMixin):
    __tablename__ = "group"
    __search_fields__: ClassVar = {"name"}
    __visible_name__ = {"en_US": "Group", "zh_CN": "用户组"}
    id: Mapped[_types.int_pk]
    name: Mapped[str]
    description: Mapped[str | None]
    role_id: Mapped[int] = mapped_column(ForeignKey(Role.id, ondelete="CASCADE"))
    role: Mapped["Role"] = relationship(backref="group", passive_deletes=True)
    user: Mapped[list["User"]] = relationship(back_populates="group")


class User(Base, AuditTimeMixin):
    __tablename__ = "user"
    __search_fields__: ClassVar = {"email", "name", "phone"}
    __visible_name__ = {"en_US": "User", "zh_CN": "用户"}
    id: Mapped[_types.int_pk]
    name: Mapped[str]
    email: Mapped[str | None] = mapped_column(unique=True)
    phone: Mapped[str | None] = mapped_column(unique=True)
    password: Mapped[str]
    avatar: Mapped[str | None]
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[_types.bool_true]
    group_id: Mapped[int] = mapped_column(ForeignKey(Group.id, ondelete="CASCADE"))
    group: Mapped["Group"] = relationship(back_populates="user", passive_deletes=True)
    role_id: Mapped[int] = mapped_column(ForeignKey(Role.id, ondelete="CASCADE"))
    role: Mapped["Role"] = relationship(backref="user", passive_deletes=True)
    auth_info: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))


Group.user_count = column_property(
    select(func.count(User.id)).where(User.group_id == Group.id).correlate_except(Group).scalar_subquery(),
    deferred=True,
)
Role.permission_count = column_property(
    select(func.count(Permission.id))
    .where(and_(RolePermission.role_id == Role.id, RolePermission.permission_id == Permission.id))
    .correlate_except(Role)
    .scalar_subquery(),
    deferred=True,
)
