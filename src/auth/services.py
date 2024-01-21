from collections.abc import Sequence

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import schemas
from src.auth.models import Group, Menu, Permission, Role, User
from src.auth.schemas import PermissionCreate, PermissionUpdate
from src.context import locale_ctx
from src.db.dtobase import DtoBase
from src.exceptions import NotFoundError, PermissionDenyError
from src.security import verify_password


class UserDto(DtoBase[User, schemas.UserCreate, schemas.UserUpdate, schemas.UserQuery]):
    async def verify_user(self, session: AsyncSession, user: OAuth2PasswordRequestForm) -> User:
        stmt = self._get_base_stmt().where(or_(self.model.email == user.username, self.model.phone == user.username))
        db_user = await session.scalar(stmt)
        if not db_user:
            raise NotFoundError(self.model.__visible_name__[locale_ctx.get()], "username", user.username)
        if not verify_password(user.password, db_user.password):
            raise PermissionDenyError
        return db_user


class GroupDto(DtoBase[Group, schemas.GroupCreate, schemas.GroupUpdate, schemas.GroupQuery]):
    async def create_with_users(
        self, session: AsyncSession, group: schemas.GroupCreate, users: Sequence[User]
    ) -> Group:
        """
        Create a new group with the specified users.

        Parameters:
            session (AsyncSession): The database session.
            group (schemas.GroupCreate): The group data to create.
            users (Sequence[User]): The list of users to associate with the group.

        Returns:
            Group: The newly created group.

        """
        new_group = await self.create(session, group, excludes={"user_ids"}, commit=False)
        new_group.user.extend(users)
        return await self.commit(session, new_group)


class RoleDto(DtoBase[Role, schemas.RoleCreate, schemas.RoleUpdate, schemas.RoleQuery]):
    async def create_with_permissions(
        self, session: AsyncSession, role: schemas.RoleCreate, permissions: Sequence[Permission]
    ) -> Role:
        """
        Create a new role with the specified permissions.

        Parameters:
            session (AsyncSession): The database session.
            role (schemas.RoleCreate): The role data to create.
            permissions (Sequence[Permission]): The list of permissions to associate with the role.

        Returns:
            Role: The newly created role.

        """
        new_role = await self.create(session, role, excludes={"permission_ids"}, commit=False)
        new_role.permission.extend(permissions)
        return await self.commit(session, new_role)


class PermissionDto(DtoBase[Permission, schemas.PermissionCreate, schemas.PermissionUpdate, schemas.PermissionQuery]):
    async def create(
        self,
        session: AsyncSession,
        obj_in: PermissionCreate,
        excludes: set[str] | None = None,
        exclude_unset: bool = False,
        exclude_none: bool = False,
        commit: bool | None = True,
    ) -> Permission:
        raise NotImplementedError

    async def update(
        self,
        session: AsyncSession,
        db_obj: Permission,
        obj_in: PermissionUpdate,
        excludes: set[str] | None = None,
        commit: bool | None = True,
    ) -> Permission:
        raise NotImplementedError

    async def delete(self, session: AsyncSession, db_obj: Permission) -> None:
        raise NotImplementedError


class MenuDto(DtoBase[Menu, schemas.MenuCreate, schemas.MenuUpdate, schemas.MenuQuery]):
    async def get_all(self, session: AsyncSession) -> Sequence[Menu]:
        return (await session.scalars(select(self.model))).all()

    @staticmethod
    def menu_tree_transform(menus: Sequence[Menu]) -> list[dict]:
        ...


user_dto = UserDto(User)
group_dto = GroupDto(Group)
role_dto = RoleDto(Role)
permission_dto = PermissionDto(Permission)
menu_dto = MenuDto(Menu)
