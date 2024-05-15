from collections.abc import Sequence

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors.auth_exceptions import NotFoundError, PermissionDenyError
from src.core.repositories import BaseRepository
from src.core.utils.context import locale_ctx
from src.features.auth import schemas
from src.features.auth.models import Group, Menu, Permission, Role, User
from src.features.auth.security import verify_password


class UserRepo(BaseRepository[User, schemas.UserCreate, schemas.UserUpdate, schemas.UserQuery]):
    async def verify_user(self, session: AsyncSession, user: OAuth2PasswordRequestForm) -> User:
        stmt = self._get_base_stmt().where(or_(self.model.email == user.username, self.model.phone == user.username))
        db_user = await session.scalar(stmt)
        if not db_user:
            raise NotFoundError(self.model.__visible_name__[locale_ctx.get()], "username", user.username)
        if not verify_password(user.password, db_user.password):
            raise PermissionDenyError
        return db_user


class PermissionRepo(
    BaseRepository[Permission, schemas.PermissionCreate, schemas.PermissionUpdate, schemas.PermissionQuery]
):
    async def create(
        self,
        session: AsyncSession,
        obj_in: schemas.PermissionCreate,
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
        obj_in: schemas.PermissionUpdate,
        excludes: set[str] | None = None,
        commit: bool | None = True,
    ) -> Permission:
        raise NotImplementedError

    async def delete(self, session: AsyncSession, db_obj: Permission) -> None:
        raise NotImplementedError


class MenuRepo(BaseRepository[Menu, schemas.MenuCreate, schemas.MenuUpdate, schemas.MenuQuery]):
    async def get_all(self, session: AsyncSession) -> Sequence[Menu]:
        return (await session.scalars(select(self.model))).all()

    @staticmethod
    def menu_tree_transform(menus: Sequence[Menu]) -> list[dict]:
        ...


class GroupRepo(BaseRepository[Group, schemas.GroupCreate, schemas.GroupUpdate, schemas.GroupQuery]):
    ...


class RoleRepo(BaseRepository[Role, schemas.RoleCreate, schemas.RoleUpdate, schemas.RoleQuery]):
    ...
