from fastapi import APIRouter

from src.features.auth.restapi import router as auth_router


def register_router() -> APIRouter:
    root_router = APIRouter()
    root_router.include_router(auth_router, prefix="/auth", tags=["Admin.Auth"])
    return root_router


router = register_router()
