from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.rbac.router import router as rbac_router
from app.modules.user.router import router as user_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(rbac_router)
v1_router.include_router(user_router)
