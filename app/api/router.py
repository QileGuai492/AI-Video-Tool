"""API 路由汇总。"""

from fastapi import APIRouter

from app.api.routes import (
    audio,
    auth,
    characters,
    cost,
    generate,
    history,
    monitor,
    previs,
    subtitle,
    templates,
    upload,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(generate.router)
api_router.include_router(characters.router)
api_router.include_router(history.router)
api_router.include_router(templates.router)
api_router.include_router(upload.router)
api_router.include_router(audio.router)
api_router.include_router(subtitle.router)
api_router.include_router(cost.router)
api_router.include_router(monitor.router)
api_router.include_router(previs.router)
