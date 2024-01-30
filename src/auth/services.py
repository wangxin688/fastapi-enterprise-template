from collections.abc import Sequence

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import schemas
from src.auth.models import Menu, Permission, User
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
