"""API 라우터 패키지"""
from fastapi import APIRouter, FastAPI

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(v1_router)


def register_routers(app: FastAPI) -> None:
    """FastAPI 앱에 라우터 등록"""
    api_router = APIRouter()
    api_router.include_router(v1_router)

    app.include_router(api_router)