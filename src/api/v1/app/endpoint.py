"""App API 라우터"""

from fastapi import APIRouter, Depends, Path

from src.api.v1.app.schemas.request import AppCreateRequest, AppRevisionRequest
from src.api.v1.app.schemas.response import AppCreateResponse, AppDeleteResponse, AppRevisionResponse
from src.api.v1.deps.user import get_user
from src.app.app.app_create_use_case import AppCreateUseCase
from src.app.app.app_delete_use_case import AppDeleteUseCase
from src.app.app.app_revision_use_case import AppRevisionUseCase
from src.core.response import SuccessResponse
from src.core.user.model import User

app_router = APIRouter(prefix="/apps", tags=["apps"])


@app_router.post("", response_model=SuccessResponse[AppCreateResponse])
async def create_app(
    payload: AppCreateRequest,
    user: User = Depends(get_user),
    app_create_usecase: AppCreateUseCase = Depends(AppCreateUseCase)
):
    """App(Deployment) 생성

    Deployment 자원을 생성합니다.
    - 컨테이너 이미지 및 리소스 제한 지정
    - 최대 리소스 (CPU, Memory) 설정 가능
    """
    app_create_result = await app_create_usecase(
        payload,
        user.id
    )
    return SuccessResponse(
        message="App created successfully",
        data=app_create_result
    )


@app_router.delete("/{namespace}/{name}", response_model=SuccessResponse[AppDeleteResponse])
async def delete_app(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_delete_usecase: AppDeleteUseCase = Depends(AppDeleteUseCase)
):
    """App(Deployment) 삭제

    Deployment 자원을 삭제합니다.
    """
    app_delete_result = await app_delete_usecase(
        name=name,
        namespace=namespace,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deleted successfully",
        data=app_delete_result
    )


@app_router.patch("/{namespace}/{name}", response_model=SuccessResponse[AppRevisionResponse])
async def revise_app(
    payload: AppRevisionRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_revision_usecase: AppRevisionUseCase = Depends(AppRevisionUseCase)
):
    """App(Deployment) 리소스 수정

    Deployment 자원량을 수정합니다.
    - CPU, Memory 리소스 조정
    - 레플리카 수 조정
    """
    app_revision_result = await app_revision_usecase(
        name=name,
        namespace=namespace,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="App revised successfully",
        data=app_revision_result
    )
