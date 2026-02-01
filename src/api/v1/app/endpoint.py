"""App API 라우터"""

from fastapi import APIRouter, Depends

from src.api.v1.app.schemas.request import AppCreateRequest
from src.api.v1.app.schemas.response import AppCreateResponse
from src.api.v1.deps.user import get_user
from src.app.app.app_create_use_case import AppCreateUseCase
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
