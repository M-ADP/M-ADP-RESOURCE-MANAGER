"""App API 라우터"""

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from src.api.v1.app.schemas.request import AppCreateRequest, AppRevisionRequest, AutoScaleRequest
from src.api.v1.app.schemas.response import AppCreateResponse, AppDeleteResponse, AppRevisionResponse, AutoScaleResponse
from src.api.v1.app.schemas.log_response import AppLogsResponse
from src.api.v1.app.schemas.event_response import AppEventsResponse
from src.api.v1.deps.user import get_user
from src.app.app.app_create_use_case import AppCreateUseCase
from src.app.app.app_delete_use_case import AppDeleteUseCase
from src.app.app.app_revision_use_case import AppRevisionUseCase
from src.app.app.app_logs_use_case import AppLogsUseCase
from src.app.app.app_events_use_case import AppEventsUseCase
from src.app.app.app_autoscale_use_case import AppAutoScaleUseCase
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


@app_router.get("/{namespace}/{name}/logs", response_model=SuccessResponse[AppLogsResponse])
async def get_app_logs(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    tail_lines: Optional[int] = Query(default=100, description="마지막 N줄만 조회"),
    since_seconds: Optional[int] = Query(default=None, description="최근 N초 동안의 로그만 조회"),
    timestamps: bool = Query(default=False, description="타임스탬프 포함 여부"),
    user: User = Depends(get_user),
    app_logs_usecase: AppLogsUseCase = Depends(AppLogsUseCase),
):
    """App(Deployment) 로그 조회

    Deployment에 속한 모든 Pod의 로그를 조회합니다.
    """
    result = await app_logs_usecase(
        name=name,
        namespace=namespace,
        tail_lines=tail_lines,
        since_seconds=since_seconds,
        timestamps=timestamps,
    )
    return SuccessResponse(
        message="App logs retrieved successfully",
        data=result,
    )


@app_router.get("/{namespace}/{name}/events", response_model=SuccessResponse[AppEventsResponse])
async def get_app_events(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_events_usecase: AppEventsUseCase = Depends(AppEventsUseCase),
):
    """App(Deployment) 이벤트 조회

    Deployment, ReplicaSet, Pod 관련 Kubernetes 이벤트를 조회합니다.
    """
    result = await app_events_usecase(
        name=name,
        namespace=namespace,
    )
    return SuccessResponse(
        message="App events retrieved successfully",
        data=result,
    )


@app_router.patch("/{namespace}/{name}/auto-scale", response_model=SuccessResponse[AutoScaleResponse])
async def set_auto_scale(
    payload: AutoScaleRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    autoscale_usecase: AppAutoScaleUseCase = Depends(AppAutoScaleUseCase),
):
    """App Auto Scale 설정 (HPA 생성/수정)

    Deployment에 HPA(Horizontal Pod Autoscaler)를 설정합니다.
    - CPU/Memory 사용률 기반 자동 스케일링
    - 최소/최대 레플리카 수 지정
    """
    result = await autoscale_usecase(
        name=name,
        namespace=namespace,
        payload=payload,
        user_id=user.id,
    )
    return SuccessResponse(
        message="Auto scale configured successfully",
        data=result,
    )
