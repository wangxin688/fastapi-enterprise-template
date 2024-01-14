from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import _types
from src.db.base import Base


class RolePermission(Base):
    __tablename__ = "role_permission"
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permission.id"), primary_key=True)


class Role(Base):
    __tablename__ = "role"
    __search_fields__: ClassVar = {"name"}
    id: Mapped[_types.int_pk]
    name: Mapped[str]
    permission: Mapped[list["Permission"]] = relationship(secondary=RolePermission, backref="role")


class Permission(Base):
    __tablename__ = "permission"
    id: Mapped[_types.int_pk]
    name: Mapped[str]
    url: Mapped[str]
    method: Mapped[str]
    tag: Mapped[str]


class Group(Base):
    __tablename__ = "group"
    __search_fields__: ClassVar = {"name"}
    id: Mapped[_types.int_pk]
    name: Mapped[str]
    role_id: Mapped[int] = mapped_column(ForeignKey(Role.id, ondelete="CASCADE"))
    role: Mapped["Role"] = relationship(backref="group", passive_deletes=True)


class User(Base):
    __tablename__ = "user"
    __search_fields__: ClassVar = {"email", "name", "phone"}
    id: Mapped[_types.int_pk]
    name: Mapped[str]
    email: Mapped[str | None] = mapped_column(unique=True)
    phone: Mapped[str | None] = mapped_column(unique=True)
    password: Mapped[str]
    avatar: Mapped[str | None]
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    group_id: Mapped[int] = mapped_column(ForeignKey(Group.id, ondelete="CASCADE"))
    group: Mapped["Group"] = relationship(backref="user", passive_deletes=True)
    role_id: Mapped[int] = mapped_column(ForeignKey(Role.id, ondelete="CASCADE"))
    role: Mapped["Role"] = relationship(backref="user", passive_deletes=True)
    auth_info: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))
