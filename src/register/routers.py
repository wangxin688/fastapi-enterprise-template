from fastapi import APIRouter

from src.features.admin.api import router as auth_router


def register_v1_router() -> APIRouter:
    root_router = APIRouter()
    root_router.include_router(auth_router, prefix="/v1/admin", tags=["Admin"])
    return root_router


router = register_v1_router()
