from datetime import datetime
from uuid import UUID

from pydantic import EmailStr
from pydantic_extra_types.phone_numbers import PhoneNumber

from src._types import AuditTimeBase, BaseModel, QueryParams


class AccessToken(BaseModel):
    token_type: str = "Bearer"
    access_token: str
    expires_at: datetime
    issued_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    refresh_token_issued_at: datetime


class Permission(BaseModel):
    id: int
    name: str
    url: str
    method: str
    tag: str


class PermissionCreate(BaseModel):
    ...


class PermissionUpdate(QueryParams):
    ...


class PermissionQuery(QueryParams):
    ...


class UserBase(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
    avatar: str | None = None


class UserBrief(UserBase):
    id: int


class GroupBase(BaseModel):
    name: str
    description: str | None = None


class GroupBrief(BaseModel):
    id: int
    name: str


class RoleBase(BaseModel):
    name: str
    slug: str
    description: str


class RoleBrief(BaseModel):
    id: int
    name: str


class MenuBase(BaseModel):
    name: str
    hidden: bool
    redirect: str
    hideChildrenInMenu: bool
    order: int
    title: str
    icon: str | None
    keepAlive: bool
    hiddenHeaderContent: bool
    permission: list[int]
    parent_id: int


class MenuCreate(MenuBase):
    id: int


class MenuUpdate(BaseModel):
    name: str | None
    hidden: bool | None
    redirect: str | None
    hideChildrenInMenu: bool | None
    order: int | None
    title: str | None
    icon: str | None
    keepAlive: bool | None
    hiddenHeaderContent: bool | None
    permission: list[int] | None
    parent_id: int | None


class MenuQuery(QueryParams):
    ...


class UserCreate(UserBase):
    group_id: int
    role_id: int | None = None


class GroupCreate(GroupBase):
    password: str
    role_id: int
    user_ids: list[int] | None = None


class RoleCreate(RoleBase):
    permission_ids: list[UUID] | None = None


class UserUpdate(UserCreate):
    name: str | None = None
    password: str | None = None
    group_id: int | None = None


class GroupUpdate(GroupCreate):
    name: str | None = None
    role_id: int | None = None


class RoleUpdate(RoleCreate):
    name: str | None = None
    description: str | None = None


class UserDetail(UserBase, AuditTimeBase):
    id: int
    role: RoleBrief
    group: GroupBrief


class GroupDetail(GroupBase, AuditTimeBase):
    id: int
    user_count: int
    role: RoleBrief


class RoleDetail(RoleBase, AuditTimeBase):
    id: int
    permission: list[Permission]
    user_count: int


class RoleList(RoleBase, AuditTimeBase):
    id: int
    permission_count: int


class UserQuery(QueryParams):
    ...


class GroupQuery(QueryParams):
    ...


class RoleQuery(QueryParams):
    ...
