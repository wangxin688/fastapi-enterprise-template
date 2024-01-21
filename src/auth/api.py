from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import errors
from src._types import IdResponse, ListT
from src.auth import schemas
from src.auth.models import Group, Permission, Role, User
from src.auth.services import group_dto, menu_dto, role_dto, user_dto
from src.cbv import cbv
from src.deps import auth, get_session
from src.exceptions import GenerError
from src.security import generate_access_token_response
from src.validators import list_to_tree

router = APIRouter()


@router.post("/pwd-login", operation_id="c5f719b1-7adf-4b4e-a498-732b8da7d758")
async def login_pwd(
    user: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> schemas.AccessToken:
    result = await user_dto.verify_user(session, user)
    return generate_access_token_response(result.id)


@cbv(router)
class UserAPI:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)

    @router.post("/users", operation_id="5091fff6-1adc-4a22-8a8c-ef0107122df7", summary="创建新用户/Create new user")
    async def create_user(self, user: schemas.UserCreate) -> IdResponse:
        new_user = await user_dto.create(self.session, user)
        result = await user_dto.commit(self.session, new_user)
        return IdResponse(id=result.id)

    @router.get(
        "/users/{id}",
        operation_id="276a8c69-2f5c-40d5-91c4-d0ddd1c24766",
        summary="获取单个用户/Get user information by ID",
    )
    async def get_user(self, id: int) -> schemas.UserDetail:
        db_user = await user_dto.get_one_or_404(
            self.session,
            id,
            selectinload(User.role).load_only(Role.id, Role.name),
            selectinload(User.group).load_only(Group.id, Group.name),
        )
        return schemas.UserDetail.model_validate(db_user)

    @router.get("/users", operation_id="2485e2a2-4d81-4601-a6fd-c633b23ce5fc")
    async def get_users(self, query: schemas.UserQuery = Depends()) -> ListT[list[schemas.UserDetail]]:
        count, results = await user_dto.list_and_count(
            self.session,
            query,
            selectinload(User.role).load_only(Role.id, Role.name),
            selectinload(User.group).load_only(Group.id, Group.name),
        )
        return ListT(count=count, results=[schemas.UserDetail.model_validate(r) for r in results])

    @router.put("/users/{id}", operation_id="ea0078b9-7f16-4b55-9264-fa7ba48737a9")
    async def update_user(self, id: int, user: schemas.UserUpdate) -> IdResponse:
        update_user = user.model_dump(exclude_unset=True)
        if "password" in update_user and update_user["password"] is None:
            raise GenerError(errors.ERR_10006, status_code=status.HTTP_406_NOT_ACCEPTABLE)
        db_user = await user_dto.get_one_or_404(self.session, id)
        await user_dto.update(self.session, db_user, user)
        return IdResponse(id=id)

    @router.delete("/users/{id}", operation_id="78e48ceb-d7cf-46fe-bf9e-d04958aade7d")
    async def delete_user(self, id: int) -> IdResponse:
        db_user = await user_dto.get_one_or_404(self.session, id)
        await user_dto.delete(self.session, db_user)
        return IdResponse(id=id)


@cbv(router)
class GroupAPI:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)

    @router.post("/groups", operation_id="9e3e639d-c694-467d-9209-717b038cf267")
    async def create_group(self, group: schemas.GroupCreate) -> IdResponse:
        if not group.user_ids:
            new_group = await group_dto.create(self.session, group)
        else:
            users = (await self.session.scalars(select(User).where(User.id.in_(group.user_ids)))).all()
            new_group = await group_dto.create_with_users(self.session, group, users)
        return IdResponse(id=new_group.id)

    @router.get("/groups/{id}", operation_id="00327087-9443-4d24-8d04-e396e3244744")
    async def get_group(self, id: int) -> schemas.GroupDetail:
        db_group = await group_dto.get_one_or_404(self.session, id, undefer_load=True)
        return schemas.GroupDetail.model_validate(db_group)

    @router.get("/groups", operation_id="a1d1f8f1-4d4d-4fab-868b-3f977df26e05")
    async def get_groups(self, query: schemas.GroupQuery = Depends()) -> ListT[list[schemas.GroupDetail]]:
        count, results = await group_dto.list_and_count(self.session, query)
        return ListT(count=count, results=[schemas.GroupDetail.model_validate(r) for r in results])

    @router.put("/groups/{id}", operation_id="3d5badd1-665c-49f8-85c4-6f6d7f3a1b2a")
    async def update_group(self, id: int, group: schemas.GroupUpdate) -> IdResponse:
        db_group = await group_dto.get_one_or_404(self.session, id, selectinload(Group.user))
        update_group = group.model_dump(exclude_unset=True)
        if "user_ids" in update_group:
            db_group = await group_dto.update_relationship_field(self.session, db_group, User, "user", group.user_ids)
        await group_dto.update(self.session, db_group, group, excludes={"user_ids"})
        return IdResponse(id=id)

    @router.delete("/groups/{id}", operation_id="e16830da-2973-4369-8e75-da9b4174ab72")
    async def delete_group(self, id: int) -> IdResponse:
        db_group = await group_dto.get_one_or_404(self.session, id)
        await group_dto.delete(self.session, db_group)
        return IdResponse(id=id)


@cbv(router)
class RoleAPI:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)

    @router.post("/roles", operation_id="a18a152b-e9e9-4128-b8be-8a8e9c842abb")
    async def create_role(self, role: schemas.RoleCreate) -> IdResponse:
        if not role.permission_ids:
            new_role = await role_dto.create(self.session, role)
        else:
            permissions = (
                await self.session.scalars(select(Permission).where(Permission.id.in_(role.permission_ids)))
            ).all()
            new_role = await role_dto.create_with_permissions(self.session, role, permissions)
        return IdResponse(id=new_role.id)

    @router.get("/roles/{id}", operation_id="2b45f59a-77a1-45d4-bf43-94373da517e3")
    async def get_role(self, id: int) -> schemas.RoleDetail:
        db_role = await role_dto.get_one_or_404(self.session, id, selectinload(Role.permission), undefer_load=True)
        return schemas.RoleDetail.model_validate(db_role)

    @router.get("/roles", operation_id="c5f793b1-7adf-4b4e-a498-732b0fa7d758")
    async def get_roles(self, query: schemas.RoleQuery = Depends()) -> ListT[list[schemas.RoleList]]:
        count, results = await role_dto.list_and_count(self.session, query)
        return ListT(count=count, results=[schemas.RoleList.model_validate(r) for r in results])

    @router.put("/roles/{id}", operation_id="2fda2e00-ad86-4296-a1d4-c7f02366b52e")
    async def update_role(self, id: int, role: schemas.RoleUpdate) -> IdResponse:
        db_role = await role_dto.get_one_or_404(self.session, id, selectinload(Role.permission))
        if "permission_ids" in role.model_dump(exclude_unset=True):
            db_role = await role_dto.update_relationship_field(
                self.session, db_role, Permission, "permission", role.permission_ids
            )
        await role_dto.update(self.session, db_role, role, excludes={"permission_ids"})
        return IdResponse(id=id)

    @router.delete("/roles/{id}", operation_id="c4e9e0e8-6b0c-4f6f-9e6c-8d9f9f9f9f9f")
    async def delete_role(self, id: int) -> IdResponse:
        db_role = await role_dto.get_one_or_404(self.session, id)
        await role_dto.delete(self.session, db_role)
        return IdResponse(id=id)


@cbv(router)
class MenuAPI:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)

    @router.post("/menus", operation_id="008bf4d4-cc01-48b0-82b8-1a67c0348b31")
    async def create_menu(self, meun: schemas.MenuCreate) -> IdResponse:
        new_menu = await menu_dto.create(self.session, meun)
        return IdResponse(id=new_menu.id)

    @router.get("/menus", operation_id="cb7f25ab-798b-4668-a838-6339425e2889")
    async def get_menus(self) -> schemas.MenuTree:
        results = await menu_dto.get_all(self.session)
        return list_to_tree([r.dict() for r in results])

    @router.put("menus/{id}", operation_id="b4d7ac97-a182-4bd1-a75c-6ae44b5fcf0a")
    async def update_menu(self, id: int, meun: schemas.MenuUpdate) -> IdResponse:
        db_menu = await menu_dto.get_one_or_404(self.session, id)
        await menu_dto.update(self.session, db_menu, meun)
        return IdResponse(id=id)

    async def delete_menu(self, id: int) -> IdResponse:
        db_menu = await menu_dto.get_one_or_404(self.session, id)
        await menu_dto.delete(self.session, db_menu)
        return IdResponse(id=id)
