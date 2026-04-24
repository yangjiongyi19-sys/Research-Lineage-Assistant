from fastapi import APIRouter

from app.api.v1.endpoints import research, wiki, workflow

api_router = APIRouter()

# 注册路由
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
api_router.include_router(wiki.router, prefix="/wiki", tags=["wiki"])
