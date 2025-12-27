"""API 라우터 등록"""

from fastapi import APIRouter, FastAPI

from api.routers import v1_router

def register_routers(app: FastAPI) -> None:
    """FastAPI 앱에 라우터 등록"""
    api_router = APIRouter()
    api_router.include_router(v1_router)

    app.include_router(api_router)
