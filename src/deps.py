from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import exceptions
from src.auth.models import RolePermission, User
from src.config import settings
from src.context import locale_ctx
from src.db.session import async_session
from src.enums import ReservedRoleSlug
from src.security import API_WHITE_LISTS, JWT_ALGORITHM, JwtTokenPayload
from src.utils.cache import CacheNamespace, redis_client

token = HTTPBearer()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def auth(request: Request, session: AsyncSession = Depends(get_session), token: str = Depends(token)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.DecodeError as e:
        raise exceptions.TokenInvalidError from e
    token_data = JwtTokenPayload(**payload)
    if token_data.refresh:
        raise exceptions.TokenInvalidError
    now = datetime.now(tz=UTC)
    if now < token_data.issued_at or now > token_data.expires_at:
        raise exceptions.TokenExpireError
    user = await session.get(User, token_data.sub, options=[selectinload(User.role)])
    if not user:
        raise exceptions.NotFoundError(User.__visible_name__[locale_ctx.get()], "id", id)
    check_user_active(user.is_active)
    operation_id = request.scope.get("operation_id")
    if not operation_id:
        raise
    privileged = check_privileged_role(user.role.slug, operation_id)
    if privileged:
        return user
    await check_role_permissions(user.role_id, session, operation_id)
    return user


def check_user_active(is_active: bool) -> None:
    if not is_active:
        raise exceptions.PermissionDenyError


def check_privileged_role(slug: str, operation_id: str) -> bool:
    if slug == ReservedRoleSlug.ADMIN:
        return True
    if operation_id in API_WHITE_LISTS:
        return True
    return False


async def check_role_permissions(role_id: int, session: AsyncSession, operation_id: str) -> None:
    permissions: list[str] | None = await redis_client.get_cache(name=str(role_id), namespace=CacheNamespace.ROLE_CACHE)
    if not permissions:
        _permissions = (
            await session.scalars(select(RolePermission.permission_id).where(RolePermission.role_id == role_id))
        ).all()
        if not _permissions:
            raise exceptions.PermissionDenyError
        permissions = [str(p) for p in _permissions]
        await redis_client.set_nx(name=str(role_id), value=permissions, namespace=CacheNamespace.ROLE_CACHE)
    if operation_id not in permissions:
        raise exceptions.PermissionDenyError
