"""App API 라우터"""

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from src.api.v1.app.schemas.request import AppCreateRequest, AppRevisionRequest, AutoScaleRequest, FixedScaleRequest, SecretCreateRequest, EnvironmentCreateRequest, EnvironmentUpdateRequest
from src.api.v1.app.schemas.response import AppCreateResponse, AppDeleteResponse, AppRevisionResponse, AutoScaleResponse, FixedScaleResponse, SecretCreateResponse, SecretDeleteResponse, EnvironmentCreateResponse, EnvironmentUpdateResponse, EnvironmentDeleteResponse
from src.api.v1.app.schemas.log_response import AppLogsResponse
from src.api.v1.app.schemas.event_response import AppEventsResponse
from src.api.v1.deps.user import get_user
from src.app.app.app_deployment_create_use_case import AppDeploymentCreateUseCase
from src.app.app.app_deployment_delete_use_case import AppDeploymentDeleteUseCase
from src.app.app.app_deployment_revision_use_case import AppDeploymentRevisionUseCase
from src.app.app.app_deployment_logs_use_case import AppDeploymentLogsUseCase
from src.app.app.app_deployment_events_use_case import AppDeploymentEventsUseCase
from src.app.app.app_deployment_autoscale_use_case import AppDeploymentAutoScaleUseCase
from src.app.app.app_deployment_fixed_scale_use_case import AppDeploymentFixedScaleUseCase
from src.app.app.app_deployment_secret_create_use_case import AppDeploymentSecretCreateUseCase
from src.app.app.app_deployment_secret_delete_use_case import AppDeploymentSecretDeleteUseCase
from src.app.app.app_deployment_environment_create_use_case import AppDeploymentEnvironmentCreateUseCase
from src.app.app.app_deployment_environment_update_use_case import AppDeploymentEnvironmentUpdateUseCase
from src.app.app.app_deployment_environment_delete_use_case import AppDeploymentEnvironmentDeleteUseCase
from src.core.response import SuccessResponse
from src.core.user.model import User

app_router = APIRouter(prefix="/apps", tags=["apps"])


@app_router.post("/{namespace}", response_model=SuccessResponse[AppCreateResponse])
async def create_app_deployment(
    payload: AppCreateRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    user: User = Depends(get_user),
    app_deployment_create_usecase: AppDeploymentCreateUseCase = Depends(AppDeploymentCreateUseCase)
):
    """App Deployment 생성

    Deployment 자원을 생성합니다.
    - 컨테이너 이미지 및 리소스 제한 지정
    - 최대 리소스 (CPU, Memory) 설정 가능
    """
    app_deployment_create_result = await app_deployment_create_usecase(
        namespace=namespace,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deployment created successfully",
        data=app_deployment_create_result
    )


@app_router.delete("/{namespace}/{name}", response_model=SuccessResponse[AppDeleteResponse])
async def delete_app_deployment(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_delete_usecase: AppDeploymentDeleteUseCase = Depends(AppDeploymentDeleteUseCase)
):
    """App Deployment 삭제

    Deployment 자원을 삭제합니다.
    """
    app_deployment_delete_result = await app_deployment_delete_usecase(
        app_name=name,
        namespace=namespace,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deployment deleted successfully",
        data=app_deployment_delete_result
    )


@app_router.patch("/{namespace}/{name}", response_model=SuccessResponse[AppRevisionResponse])
async def revise_app_deployment(
    payload: AppRevisionRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_revision_usecase: AppDeploymentRevisionUseCase = Depends(AppDeploymentRevisionUseCase)
):
    """App Deployment 리소스 수정

    Deployment 자원량을 수정합니다.
    - CPU, Memory 리소스 조정
    - 레플리카 수 조정
    """
    app_deployment_revision_result = await app_deployment_revision_usecase(
        app_name=name,
        namespace=namespace,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deployment revised successfully",
        data=app_deployment_revision_result
    )


@app_router.get("/{namespace}/{name}/logs", response_model=SuccessResponse[AppLogsResponse])
async def get_app_deployment_logs(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    tail_lines: Optional[int] = Query(default=100, description="마지막 N줄만 조회"),
    since_seconds: Optional[int] = Query(default=None, description="최근 N초 동안의 로그만 조회"),
    timestamps: bool = Query(default=False, description="타임스탬프 포함 여부"),
    user: User = Depends(get_user),
    app_deployment_logs_usecase: AppDeploymentLogsUseCase = Depends(AppDeploymentLogsUseCase),
):
    """App Deployment 로그 조회

    Deployment에 속한 모든 Pod의 로그를 조회합니다.
    """
    app_deployment_logs_result = await app_deployment_logs_usecase(
        app_name=name,
        namespace=namespace,
        tail_lines=tail_lines,
        since_seconds=since_seconds,
        timestamps=timestamps,
    )
    return SuccessResponse(
        message="App deployment logs retrieved successfully",
        data=app_deployment_logs_result,
    )


@app_router.get("/{namespace}/{name}/events", response_model=SuccessResponse[AppEventsResponse])
async def get_app_deployment_events(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_events_usecase: AppDeploymentEventsUseCase = Depends(AppDeploymentEventsUseCase),
):
    """App Deployment 이벤트 조회

    Deployment, ReplicaSet, Pod 관련 Kubernetes 이벤트를 조회합니다.
    """
    app_deployment_events_result = await app_deployment_events_usecase(
        app_name=name,
        namespace=namespace,
    )
    return SuccessResponse(
        message="App deployment events retrieved successfully",
        data=app_deployment_events_result,
    )


@app_router.patch("/{namespace}/{name}/auto-scale", response_model=SuccessResponse[AutoScaleResponse])
async def set_app_deployment_auto_scale(
    payload: AutoScaleRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_autoscale_usecase: AppDeploymentAutoScaleUseCase = Depends(AppDeploymentAutoScaleUseCase),
):
    """App Deployment Auto Scale 설정 (HPA 생성/수정)

    Deployment에 HPA(Horizontal Pod Autoscaler)를 설정합니다.
    - CPU/Memory 사용률 기반 자동 스케일링
    - 최소/최대 레플리카 수 지정
    """
    app_deployment_autoscale_result = await app_deployment_autoscale_usecase(
        app_name=name,
        namespace=namespace,
        payload=payload,
        user_id=user.id,
    )
    return SuccessResponse(
        message="App deployment auto scale configured successfully",
        data=app_deployment_autoscale_result,
    )


@app_router.patch("/{namespace}/{name}/fixed-scale", response_model=SuccessResponse[FixedScaleResponse])
async def set_app_deployment_fixed_scale(
    payload: FixedScaleRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_fixed_scale_usecase: AppDeploymentFixedScaleUseCase = Depends(AppDeploymentFixedScaleUseCase),
):
    """App Deployment Fixed Scale 설정 (고정 레플리카)

    Deployment의 레플리카 수를 고정값으로 설정합니다.
    - HPA가 존재하면 삭제
    - 고정 레플리카 수 지정
    """
    app_deployment_fixed_scale_result = await app_deployment_fixed_scale_usecase(
        app_name=name,
        namespace=namespace,
        payload=payload,
        user_id=user.id,
    )
    return SuccessResponse(
        message="App deployment fixed scale configured successfully",
        data=app_deployment_fixed_scale_result,
    )


@app_router.post("/{namespace}/{name}/secrets", response_model=SuccessResponse[SecretCreateResponse])
async def create_app_deployment_secret(
    payload: SecretCreateRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_secret_create_usecase: AppDeploymentSecretCreateUseCase = Depends(AppDeploymentSecretCreateUseCase)
):
    """App Deployment Secret 생성 및 Vault 설정

    Vault에 Secret을 저장하고, Pod가 접근할 수 있도록 Policy와 Role을 자동 설정합니다.
    """
    app_deployment_secret_create_result = await app_deployment_secret_create_usecase(
        namespace=namespace,
        app_name=name,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deployment secret created and configured successfully",
        data=app_deployment_secret_create_result
    )


@app_router.delete("/{namespace}/{name}/secrets/{secret_name}", response_model=SuccessResponse[SecretDeleteResponse])
async def delete_app_deployment_secret(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    secret_name: str = Path(..., description="삭제할 Secret 이름"),
    user: User = Depends(get_user),
    app_deployment_secret_delete_usecase: AppDeploymentSecretDeleteUseCase = Depends(AppDeploymentSecretDeleteUseCase)
):
    """App Deployment Secret 삭제

    Vault에서 Secret을 삭제합니다.
    만약 해당 App의 모든 Secret이 삭제되면, 관련된 Policy와 Role도 자동으로 정리됩니다.
    """
    app_deployment_secret_delete_result = await app_deployment_secret_delete_usecase(
        namespace=namespace,
        app_name=name,
        secret_name=secret_name,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deployment secret deleted successfully",
        data=app_deployment_secret_delete_result
    )


@app_router.post("/{namespace}/{name}/environment", response_model=SuccessResponse[EnvironmentCreateResponse])
async def create_app_deployment_environment(
    payload: EnvironmentCreateRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_environment_create_usecase: AppDeploymentEnvironmentCreateUseCase = Depends(AppDeploymentEnvironmentCreateUseCase)
):
    """App Deployment 환경 변수 추가 (ConfigMap 생성)

    App의 환경 변수를 ConfigMap으로 생성합니다.
    - 이미 존재하는 ConfigMap이 있으면 데이터를 병합합니다.
    - ConfigMap 이름은 {app-name}-env 형식으로 생성됩니다.
    """
    app_deployment_environment_create_result = await app_deployment_environment_create_usecase(
        namespace=namespace,
        app_name=name,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deployment environment variables created successfully",
        data=app_deployment_environment_create_result
    )


@app_router.put("/{namespace}/{name}/environment", response_model=SuccessResponse[EnvironmentUpdateResponse])
async def update_app_deployment_environment(
    payload: EnvironmentUpdateRequest,
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_environment_update_usecase: AppDeploymentEnvironmentUpdateUseCase = Depends(AppDeploymentEnvironmentUpdateUseCase)
):
    """App Deployment 환경 변수 수정 (ConfigMap 데이터 교체)

    App의 환경 변수 ConfigMap 데이터를 완전히 교체합니다.
    - 기존 데이터는 모두 삭제되고 새로운 데이터로 교체됩니다.
    - ConfigMap이 존재하지 않으면 404 에러를 반환합니다.
    """
    app_deployment_environment_update_result = await app_deployment_environment_update_usecase(
        namespace=namespace,
        app_name=name,
        payload=payload,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deployment environment variables updated successfully",
        data=app_deployment_environment_update_result
    )


@app_router.delete("/{namespace}/{name}/environment", response_model=SuccessResponse[EnvironmentDeleteResponse])
async def delete_app_deployment_environment(
    namespace: str = Path(..., description="네임스페이스 (프로젝트)"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    user: User = Depends(get_user),
    app_deployment_environment_delete_usecase: AppDeploymentEnvironmentDeleteUseCase = Depends(AppDeploymentEnvironmentDeleteUseCase)
):
    """App Deployment 환경 변수 삭제 (ConfigMap 삭제)

    App의 환경 변수 ConfigMap을 삭제합니다.
    - ConfigMap이 존재하지 않으면 404 에러를 반환합니다.
    """
    app_deployment_environment_delete_result = await app_deployment_environment_delete_usecase(
        namespace=namespace,
        app_name=name,
        user_id=user.id
    )
    return SuccessResponse(
        message="App deployment environment variables deleted successfully",
        data=app_deployment_environment_delete_result
    )
