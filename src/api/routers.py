"""API 라우터 패키지"""
from fastapi import APIRouter, FastAPI


def register_routers(app: FastAPI) -> None:
    from src.api.infra import infra_router
    from src.api.v1.project.endpoint import project_router
    from src.api.v1.app.endpoint import app_router

    v1_router = APIRouter() # prefix="/v1")
    v1_router.include_router(project_router)
    v1_router.include_router(app_router)

    root_router = APIRouter()
    # 등록할 라우터는 최종적으로 여기서 조립
    root_router.include_router(v1_router)
    root_router.include_router(infra_router)
    # ----------------------------

    app.include_router(root_router)
