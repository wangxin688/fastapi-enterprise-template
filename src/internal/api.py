from fastapi import APIRouter, Request
from sqlalchemy import delete, select

from src.auth import schemas
from src.auth.models import Permission
from src.core._types import ResultT
from src.deps import AuthUser, SqlaSession

router = APIRouter()


@router.get("/permissions", operation_id="8057d614-150f-42ee-984c-d0af35796da3")
async def get_permissions(session: SqlaSession, user: AuthUser) -> ResultT[list[schemas.Permission]]:
    permissions = (await session.scalars(select(Permission))).all()
    return ResultT(data=[schemas.Permission.model_validate(p) for p in permissions])


@router.post("/permissions", operation_id="e0fe80d5-cbe0-4c2c-9eff-57e80ecba522")
async def sync_db_permission(session: SqlaSession, user: AuthUser, request: Request) -> ResultT[dict]:
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
    permissions = (await session.scalars(select(Permission).where(Permission.id.in_(operation_ids)))).all()
    removed = {str(p.id) for p in permissions} - set(operation_ids)
    added = set(operation_ids) - {str(p.id) for p in permissions}
    if removed:
        await session.execute(delete(Permission).where(Permission.id.in_(removed)))
    if added:
        new_permissions = [Permission(id=p_id, **router_mappings[p_id]) for p_id in added]
        session.add_all(new_permissions)
        await session.commit()
    return ResultT(data={"added": added, "removed": removed})
