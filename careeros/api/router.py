"""Main API router — mounts all sub-routers."""
from fastapi import APIRouter
from careeros.api.auth.router import router as auth_router
from careeros.api.vault.router import router as vault_router
from careeros.api.jd.router import router as jd_router
from careeros.api.generation.router import router as generation_router
from careeros.api.tracker.router import router as tracker_router
from careeros.api.chat.router import router as chat_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(vault_router)
api_router.include_router(jd_router)
api_router.include_router(generation_router)
api_router.include_router(tracker_router)
api_router.include_router(chat_router)
