from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core._types import IdResponse, ListT
from src.core.errors import base_exceptions
from src.core.errors.auth_exceptions import GenerError
from src.core.utils.cbv import cbv
from src.core.utils.validators import list_to_tree
from src.deps import auth, get_session
from src.features.auth import schemas
from src.features.auth.models import Group, Menu, Permission, Role, User
from src.features.auth.repository import GroupRepo, MenuRepo, PermissionRepo, RoleRepo, UserRepo
from src.features.auth.security import generate_access_token_response

router = APIRouter()


@router.post("/pwd-login", operation_id="c5f719b1-7adf-4b4e-a498-732b8da7d758")
async def login_pwd(
    user: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> schemas.AccessToken:
    dto = UserRepo(User)
    result = await dto.verify_user(session, user)
    return generate_access_token_response(result.id)


@cbv(router)
class UserAPI:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)
    dto = UserRepo(User)

    @router.post("/users", operation_id="5091fff6-1adc-4a22-8a8c-ef0107122df7", summary="创建新用户/Create new user")
    async def create_user(self, user: schemas.UserCreate) -> IdResponse:
        new_user = await self.dto.create(self.session, user)
        result = await self.dto.commit(self.session, new_user)
        return IdResponse(id=result.id)

    @router.get(
        "/users/{id}",
        operation_id="276a8c69-2f5c-40d5-91c4-d0ddd1c24766",
        summary="获取单个用户/Get user information by ID",
    )
    async def get_user(self, id: int) -> schemas.UserDetail:
        db_user = await self.dto.get_one_or_404(
            self.session,
            id,
            selectinload(User.role).load_only(Role.id, Role.name),
            selectinload(User.group).load_only(Group.id, Group.name),
        )
        return schemas.UserDetail.model_validate(db_user)

    @router.get("/users", operation_id="2485e2a2-4d81-4601-a6fd-c633b23ce5fc")
    async def get_users(self, query: schemas.UserQuery = Depends()) -> ListT[schemas.UserDetail]:
        count, results = await self.dto.list_and_count(
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
            raise GenerError(base_exceptions.ERR_10005, status_code=status.HTTP_406_NOT_ACCEPTABLE)
        db_user = await self.dto.get_one_or_404(self.session, id)
        await self.dto.update(self.session, db_user, user)
        return IdResponse(id=id)

    @router.delete("/users/{id}", operation_id="78e48ceb-d7cf-46fe-bf9e-d04958aade7d")
    async def delete_user(self, id: int) -> IdResponse:
        db_user = await self.dto.get_one_or_404(self.session, id)
        await self.dto.delete(self.session, db_user)
        return IdResponse(id=id)


@cbv(router)
class GroupAPI:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)
    dto = GroupRepo(Group)

    @router.post("/groups", operation_id="9e3e639d-c694-467d-9209-717b038cf267")
    async def create_group(self, group: schemas.GroupCreate) -> IdResponse:
        new_group = await self.dto.create(self.session, group)
        return IdResponse(id=new_group.id)

    @router.get("/groups/{id}", operation_id="00327087-9443-4d24-8d04-e396e3244744")
    async def get_group(self, id: int) -> schemas.GroupDetail:
        db_group = await self.dto.get_one_or_404(self.session, id, undefer_load=True)
        return schemas.GroupDetail.model_validate(db_group)

    @router.get("/groups", operation_id="a1d1f8f1-4d4d-4fab-868b-3f977df26e05")
    async def get_groups(self, query: schemas.GroupQuery = Depends()) -> ListT[schemas.GroupDetail]:
        count, results = await self.dto.list_and_count(self.session, query)
        return ListT(count=count, results=[schemas.GroupDetail.model_validate(r) for r in results])

    @router.put("/groups/{id}", operation_id="3d5badd1-665c-49f8-85c4-6f6d7f3a1b2a")
    async def update_group(self, id: int, group: schemas.GroupUpdate) -> IdResponse:
        db_group = await self.dto.get_one_or_404(self.session, id, selectinload(Group.user))
        await self.dto.update(self.session, db_group, group)
        return IdResponse(id=id)

    @router.delete("/groups/{id}", operation_id="e16830da-2973-4369-8e75-da9b4174ab72")
    async def delete_group(self, id: int) -> IdResponse:
        db_group = await self.dto.get_one_or_404(self.session, id)
        await self.dto.delete(self.session, db_group)
        return IdResponse(id=id)


@cbv(router)
class RoleAPI:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)
    dto = RoleRepo(Role)

    @router.post("/roles", operation_id="a18a152b-e9e9-4128-b8be-8a8e9c842abb")
    async def create_role(self, role: schemas.RoleCreate) -> IdResponse:
        new_role = await self.dto.create(self.session, role)
        return IdResponse(id=new_role.id)

    @router.get("/roles/{id}", operation_id="2b45f59a-77a1-45d4-bf43-94373da517e3")
    async def get_role(self, id: int) -> schemas.RoleDetail:
        db_role = await self.dto.get_one_or_404(self.session, id, selectinload(Role.permission), undefer_load=True)
        return schemas.RoleDetail.model_validate(db_role)

    @router.get("/roles", operation_id="c5f793b1-7adf-4b4e-a498-732b0fa7d758")
    async def get_roles(self, query: schemas.RoleQuery = Depends()) -> ListT[schemas.RoleList]:
        count, results = await self.dto.list_and_count(self.session, query)
        return ListT(count=count, results=[schemas.RoleList.model_validate(r) for r in results])

    @router.put("/roles/{id}", operation_id="2fda2e00-ad86-4296-a1d4-c7f02366b52e")
    async def update_role(self, id: int, role: schemas.RoleUpdate) -> IdResponse:
        db_role = await self.dto.get_one_or_404(self.session, id, selectinload(Role.permission))
        await self.dto.update(self.session, db_role, role)
        return IdResponse(id=id)

    @router.delete("/roles/{id}", operation_id="c4e9e0e8-6b0c-4f6f-9e6c-8d9f9f9f9f9f")
    async def delete_role(self, id: int) -> IdResponse:
        db_role = await self.dto.get_one_or_404(self.session, id)
        await self.dto.delete(self.session, db_role)
        return IdResponse(id=id)


@cbv(router)
class MenuAPI:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)
    dto = MenuRepo(Menu)

    @router.post("/menus", operation_id="008bf4d4-cc01-48b0-82b8-1a67c0348b31")
    async def create_menu(self, meun: schemas.MenuCreate) -> IdResponse:
        new_menu = await self.dto.create(self.session, meun)
        return IdResponse(id=new_menu.id)

    @router.get("/menus", operation_id="cb7f25ab-798b-4668-a838-6339425e2889")
    async def get_menus(self) -> schemas.MenuTree:
        results = await self.dto.get_all(self.session)
        data = list_to_tree([r.dict() for r in results])
        return schemas.MenuTree.model_validate(data)

    @router.put("menus/{id}", operation_id="b4d7ac97-a182-4bd1-a75c-6ae44b5fcf0a")
    async def update_menu(self, id: int, meun: schemas.MenuUpdate) -> IdResponse:
        db_menu = await self.dto.get_one_or_404(self.session, id)
        await self.dto.update(self.session, db_menu, meun)
        return IdResponse(id=id)

    async def delete_menu(self, id: int) -> IdResponse:
        db_menu = await self.dto.get_one_or_404(self.session, id)
        await self.dto.delete(self.session, db_menu)
        return IdResponse(id=id)


@cbv(router)
class PermissionCBV:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)
    dto = PermissionRepo(Permission)

    @router.get("/permissions", operation_id="8057d614-150f-42ee-984c-d0af35796da3")
    async def get_permissions(self) -> ListT[schemas.Permission]:
        permissions = await self.dto.get_all(self.session)
        return ListT(results=[schemas.Permission.model_validate(p) for p in permissions], count=len(permissions))

    @router.post("/permissions", operation_id="e0fe80d5-cbe0-4c2c-9eff-57e80ecba522")
    async def sync_db_permission(self, request: Request) -> dict[str, set[str]]:
        routes = request.app.routes
        operation_ids = [route.operation_id for route in routes]
        router_mappings = {
            router.operation_id: {
                "name": router.name,
                "path": router.path,
                "methods": router.methods,
                "description": router.description,
            }
            for router in routes
        }
        permissions = await self.dto.get_multi_by_ids(self.session, operation_ids)
        removed = {str(p.id) for p in permissions} - set(operation_ids)
        added = set(operation_ids) - {str(p.id) for p in permissions}
        if removed:
            await self.dto.get_multi_and_delete(self.session, [UUID(p_id) for p_id in removed])
        if added:
            new_permissions = [Permission(id=p_id, **router_mappings[p_id]) for p_id in added]
            await self.dto.batch_commit(self.session, new_permissions)
        return {"added": added, "removed": removed}
