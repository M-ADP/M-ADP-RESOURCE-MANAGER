"""App API 라우터"""

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from src.api.v1.app.schemas.request import AppCreateRequest, AppRevisionRequest, AutoScaleRequest, FixedScaleRequest, SecretCreateRequest, EnvironmentCreateRequest, EnvironmentUpdateRequest
from src.api.v1.app.schemas.response import AppCreateResponse, AppDeleteResponse, AppRevisionResponse, AutoScaleResponse, FixedScaleResponse, SecretCreateResponse, SecretDeleteResponse, EnvironmentCreateResponse, EnvironmentUpdateResponse, EnvironmentDeleteResponse
from src.api.v1.app.schemas.log_response import AppLogsResponse
from src.api.v1.app.schemas.event_response import AppEventsResponse
from src.api.v1.deps.user import get_user
from src.app.app.app_create_use_case import AppCreateUseCase
from src.app.app.app_delete_use_case import AppDeleteUseCase
from src.app.app.app_revision_use_case import AppRevisionUseCase
from src.app.app.app_logs_use_case import AppLogsUseCase
from src.app.app.app_events_use_case import AppEventsUseCase
from src.app.app.app_autoscale_use_case import AppAutoScaleUseCase
from src.app.app.app_fixed_scale_use_case import AppFixedScaleUseCase
from src.app.app.app_secret_create_use_case import AppSecretCreateUseCase
from src.app.app.app_secret_delete_use_case import AppSecretDeleteUseCase
from src.app.app.app_environment_create_use_case import AppEnvironmentCreateUseCase
from src.app.app.app_environment_update_use_case import AppEnvironmentUpdateUseCase
from src.app.app.app_environment_delete_use_case import AppEnvironmentDeleteUseCase
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


@app_router.patch("/{namespace}/{name}/fixed-scale", response_model=SuccessResponse[FixedScaleResponse])
async def set_fixed_scale(
    payload: FixedScaleRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    fixed_scale_usecase: AppFixedScaleUseCase = Depends(AppFixedScaleUseCase),
):
    """App Fixed Scale 설정 (고정 레플리카)

    Deployment의 레플리카 수를 고정값으로 설정합니다.
    - HPA가 존재하면 삭제
    - 고정 레플리카 수 지정
    """
    result = await fixed_scale_usecase(
        name=name,
        namespace=namespace,
        payload=payload,
        user_id=user.id,
    )
    return SuccessResponse(
        message="Fixed scale configured successfully",
        data=result,
    )


@app_router.post("/{namespace}/{name}/secrets", response_model=SuccessResponse[SecretCreateResponse])
async def create_app_secret(
    payload: SecretCreateRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_secret_create_usecase: AppSecretCreateUseCase = Depends(AppSecretCreateUseCase)
):
    """App Secret 생성 및 Vault 설정

    Vault에 Secret을 저장하고, Pod가 접근할 수 있도록 Policy와 Role을 자동 설정합니다.
    """
    result = await app_secret_create_usecase(
        namespace=namespace,
        app_name=name,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="Secret created and configured successfully",
        data=result
    )


@app_router.delete("/{namespace}/{name}/secrets/{secret_name}", response_model=SuccessResponse[SecretDeleteResponse])
async def delete_app_secret(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    secret_name: str = Path(..., description="삭제할 Secret 이름"),
    user: User = Depends(get_user),
    app_secret_delete_usecase: AppSecretDeleteUseCase = Depends(AppSecretDeleteUseCase)
):
    """App Secret 삭제

    Vault에서 Secret을 삭제합니다.
    만약 해당 App의 모든 Secret이 삭제되면, 관련된 Policy와 Role도 자동으로 정리됩니다.
    """
    result = await app_secret_delete_usecase(
        namespace=namespace,
        app_name=name,
        secret_name=secret_name,
        user_id=user.id
    )
    return SuccessResponse(
        message="Secret deleted successfully",
        data=result
    )


@app_router.post("/{namespace}/{name}/environment", response_model=SuccessResponse[EnvironmentCreateResponse])
async def create_app_environment(
    payload: EnvironmentCreateRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_environment_create_usecase: AppEnvironmentCreateUseCase = Depends(AppEnvironmentCreateUseCase)
):
    """App 환경 변수 추가 (ConfigMap 생성)

    App의 환경 변수를 ConfigMap으로 생성합니다.
    - 이미 존재하는 ConfigMap이 있으면 데이터를 병합합니다.
    - ConfigMap 이름은 {app-name}-env 형식으로 생성됩니다.
    """
    result = await app_environment_create_usecase(
        namespace=namespace,
        app_name=name,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="Environment variables created successfully",
        data=result
    )


@app_router.put("/{namespace}/{name}/environment", response_model=SuccessResponse[EnvironmentUpdateResponse])
async def update_app_environment(
    payload: EnvironmentUpdateRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_environment_update_usecase: AppEnvironmentUpdateUseCase = Depends(AppEnvironmentUpdateUseCase)
):
    """App 환경 변수 수정 (ConfigMap 데이터 교체)

    App의 환경 변수 ConfigMap 데이터를 완전히 교체합니다.
    - 기존 데이터는 모두 삭제되고 새로운 데이터로 교체됩니다.
    - ConfigMap이 존재하지 않으면 404 에러를 반환합니다.
    """
    result = await app_environment_update_usecase(
        namespace=namespace,
        app_name=name,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="Environment variables updated successfully",
        data=result
    )


@app_router.delete("/{namespace}/{name}/environment", response_model=SuccessResponse[EnvironmentDeleteResponse])
async def delete_app_environment(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_environment_delete_usecase: AppEnvironmentDeleteUseCase = Depends(AppEnvironmentDeleteUseCase)
):
    """App 환경 변수 삭제 (ConfigMap 삭제)

    App의 환경 변수 ConfigMap을 삭제합니다.
    - ConfigMap이 존재하지 않으면 404 에러를 반환합니다.
    """
    result = await app_environment_delete_usecase(
        namespace=namespace,
        app_name=name,
        user_id=user.id
    )
    return SuccessResponse(
        message="Environment variables deleted successfully",
        data=result
    )
