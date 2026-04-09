"""App API 라우터"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query

from src.api.v1.app.schemas.request import (
    AppCreateRequest,
    AppRevisionRequest,
    AutoScaleRequest,
    FixedScaleRequest,
    SecretCreateRequest,
    EnvironmentUpdateRequest,
)
from src.api.v1.app.schemas.response import (
    AppCreateResponse,
    AppDeleteResponse,
    AppRevisionResponse,
    AutoScaleResponse,
    FixedScaleResponse,
    SecretCreateResponse,
    SecretDeleteResponse,
    EnvironmentUpdateResponse,
    EnvironmentDeleteResponse,
    AppRestartResponse,
)
from src.api.v1.app.schemas.log_response import AppLogsResponse
from src.api.v1.app.schemas.event_response import AppEventsResponse
from src.app.monitoring.dto import AppResourceStatusResponse
from src.app.app_deployment.app_deployment_create_use_case import (
    AppDeploymentCreateUseCase,
)
from src.app.app_deployment.app_deployment_delete_use_case import (
    AppDeploymentDeleteUseCase,
)
from src.app.app_deployment.app_deployment_revision_use_case import (
    AppDeploymentRevisionUseCase,
)
from src.app.app_deployment.app_deployment_logs_use_case import AppDeploymentLogsUseCase
from src.app.app_deployment.app_deployment_events_use_case import (
    AppDeploymentEventsUseCase,
)
from src.app.monitoring.app_resource_status_use_case import AppResourceStatusUseCase
from src.app.app_deployment.app_deployment_autoscale_use_case import (
    AppDeploymentAutoScaleUseCase,
)
from src.app.app_deployment.app_deployment_fixed_scale_use_case import (
    AppDeploymentFixedScaleUseCase,
)
from src.app.app_deployment.app_deployment_secret_create_use_case import (
    AppDeploymentSecretCreateUseCase,
)
from src.app.app_deployment.app_deployment_secret_delete_use_case import (
    AppDeploymentSecretDeleteUseCase,
)
from src.app.app_deployment.app_deployment_environment_update_use_case import (
    AppDeploymentEnvironmentUpdateUseCase,
)
from src.app.app_deployment.app_deployment_environment_delete_use_case import (
    AppDeploymentEnvironmentDeleteUseCase,
)
from src.app.app_deployment.app_deployment_restart_use_case import (
    AppDeploymentRestartUseCase,
)
from src.core.response import SuccessResponse

app_router = APIRouter(prefix="/apps", tags=["apps"])


@app_router.post("/{project_id}", response_model=SuccessResponse[AppCreateResponse])
async def create_app_deployment(
    payload: AppCreateRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    app_deployment_create_usecase: AppDeploymentCreateUseCase = Depends(
        AppDeploymentCreateUseCase
    ),
):
    """App Deployment 생성

    Deployment 자원을 생성합니다.
    - 컨테이너 이미지 및 리소스 제한 지정
    - 최대 리소스 (CPU, Memory) 설정 가능
    """
    app_deployment_create_result = await app_deployment_create_usecase(
        project_id=project_id,
        payload=payload,
    )
    return SuccessResponse(
        message="App deployment created successfully", data=app_deployment_create_result
    )


@app_router.delete(
    "/{project_id}/{name}", response_model=SuccessResponse[AppDeleteResponse]
)
async def delete_app_deployment(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_delete_usecase: AppDeploymentDeleteUseCase = Depends(
        AppDeploymentDeleteUseCase
    ),
):
    """App Deployment 삭제

    Deployment 자원을 삭제합니다.
    """
    app_deployment_delete_result = await app_deployment_delete_usecase(
        app_name=name,
        project_id=project_id,
    )
    return SuccessResponse(
        message="App deployment deleted successfully", data=app_deployment_delete_result
    )


@app_router.patch(
    "/{project_id}/{name}", response_model=SuccessResponse[AppRevisionResponse]
)
async def revise_app_deployment(
    payload: AppRevisionRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_revision_usecase: AppDeploymentRevisionUseCase = Depends(
        AppDeploymentRevisionUseCase
    ),
):
    """App Deployment 리소스 수정

    Deployment 자원량을 수정합니다.
    - CPU, Memory 리소스 조정
    - 레플리카 수 조정
    """
    app_deployment_revision_result = await app_deployment_revision_usecase(
        app_name=name,
        project_id=project_id,
        payload=payload,
    )
    return SuccessResponse(
        message="App deployment revised successfully",
        data=app_deployment_revision_result,
    )


@app_router.get(
    "/{project_id}/{name}/logs", response_model=SuccessResponse[AppLogsResponse]
)
async def get_app_deployment_logs(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    tail_lines: Optional[int] = Query(default=100, description="마지막 N줄만 조회"),
    since_seconds: Optional[int] = Query(
        default=None, description="최근 N초 동안의 로그만 조회"
    ),
    timestamps: bool = Query(default=False, description="타임스탬프 포함 여부"),
    app_deployment_logs_usecase: AppDeploymentLogsUseCase = Depends(
        AppDeploymentLogsUseCase
    ),
):
    """App Deployment 로그 조회

    Deployment에 속한 모든 Pod의 로그를 조회합니다.
    """
    app_deployment_logs_result = await app_deployment_logs_usecase(
        app_name=name,
        project_id=project_id,
        tail_lines=tail_lines,
        since_seconds=since_seconds,
        timestamps=timestamps,
    )
    return SuccessResponse(
        message="App deployment logs retrieved successfully",
        data=app_deployment_logs_result,
    )


@app_router.get(
    "/{project_id}/{name}/events", response_model=SuccessResponse[AppEventsResponse]
)
async def get_app_deployment_events(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_events_usecase: AppDeploymentEventsUseCase = Depends(
        AppDeploymentEventsUseCase
    ),
):
    """App Deployment 이벤트 조회

    Deployment, ReplicaSet, Pod 관련 Kubernetes 이벤트를 조회합니다.
    """
    app_deployment_events_result = await app_deployment_events_usecase(
        app_name=name,
        project_id=project_id,
    )
    return SuccessResponse(
        message="App deployment events retrieved successfully",
        data=app_deployment_events_result,
    )


@app_router.get(
    "/{project_id}/resource",
    response_model=SuccessResponse[List[AppResourceStatusResponse]],
)
async def get_app_deployment_resource(
    project_id: str = Path(..., description="프로젝트 ID"),
    names: List[str] = Query(..., description="App 이름 목록 (Deployment 이름)"),
    app_resource_status_usecase: AppResourceStatusUseCase = Depends(
        AppResourceStatusUseCase
    ),
):
    """App Deployment 리소스 상태 조회

    여러 Deployment의 리소스 설정(Request/Limit)과 현재 상태(Replicas)를 조회합니다.
    존재하지 않는 앱은 결과에서 제외됩니다.
    """
    app_resource_status_result = await app_resource_status_usecase(
        project_id=project_id,
        app_ids=names,
    )
    return SuccessResponse(
        message="App deployment resource status retrieved successfully",
        data=app_resource_status_result,
    )


@app_router.patch(
    "/{project_id}/{name}/auto-scale", response_model=SuccessResponse[AutoScaleResponse]
)
async def set_app_deployment_auto_scale(
    payload: AutoScaleRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_autoscale_usecase: AppDeploymentAutoScaleUseCase = Depends(
        AppDeploymentAutoScaleUseCase
    ),
):
    """App Deployment Auto Scale 설정 (HPA 생성/수정)

    Deployment에 HPA(Horizontal Pod Autoscaler)를 설정합니다.
    - CPU/Memory 사용률 기반 자동 스케일링
    - 최소/최대 레플리카 수 지정
    """
    app_deployment_autoscale_result = await app_deployment_autoscale_usecase(
        app_name=name,
        project_id=project_id,
        payload=payload,
    )
    return SuccessResponse(
        message="App deployment auto scale configured successfully",
        data=app_deployment_autoscale_result,
    )


@app_router.patch(
    "/{project_id}/{name}/fixed-scale",
    response_model=SuccessResponse[FixedScaleResponse],
)
async def set_app_deployment_fixed_scale(
    payload: FixedScaleRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_fixed_scale_usecase: AppDeploymentFixedScaleUseCase = Depends(
        AppDeploymentFixedScaleUseCase
    ),
):
    """App Deployment Fixed Scale 설정 (고정 레플리카)

    Deployment의 레플리카 수를 고정값으로 설정합니다.
    - HPA가 존재하면 삭제
    - 고정 레플리카 수 지정
    """
    app_deployment_fixed_scale_result = await app_deployment_fixed_scale_usecase(
        app_name=name,
        project_id=project_id,
        payload=payload,
    )
    return SuccessResponse(
        message="App deployment fixed scale configured successfully",
        data=app_deployment_fixed_scale_result,
    )


@app_router.post(
    "/{project_id}/{name}/secrets", response_model=SuccessResponse[SecretCreateResponse]
)
async def create_app_deployment_secret(
    payload: SecretCreateRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_secret_create_usecase: AppDeploymentSecretCreateUseCase = Depends(
        AppDeploymentSecretCreateUseCase
    ),
):
    """App Deployment Secret 생성 및 Vault 설정

    Vault에 Secret을 저장하고, Pod가 접근할 수 있도록 Policy와 Role을 자동 설정합니다.
    """
    app_deployment_secret_create_result = await app_deployment_secret_create_usecase(
        project_id=project_id,
        app_name=name,
        payload=payload,
    )
    return SuccessResponse(
        message="App deployment secret created and configured successfully",
        data=app_deployment_secret_create_result,
    )


@app_router.delete(
    "/{project_id}/{name}/secrets",
    response_model=SuccessResponse[SecretDeleteResponse],
)
async def delete_app_deployment_secret(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_secret_delete_usecase: AppDeploymentSecretDeleteUseCase = Depends(
        AppDeploymentSecretDeleteUseCase
    ),
):
    """App Deployment Secret 삭제

    Vault에서 Secret을 삭제하고, 관련된 Policy와 Role도 함께 정리합니다.
    """
    app_deployment_secret_delete_result = await app_deployment_secret_delete_usecase(
        project_id=project_id,
        app_name=name,
    )
    return SuccessResponse(
        message="App deployment secret deleted successfully",
        data=app_deployment_secret_delete_result,
    )


@app_router.put(
    "/{project_id}/{name}/environment",
    response_model=SuccessResponse[EnvironmentUpdateResponse],
)
async def update_app_deployment_environment(
    payload: EnvironmentUpdateRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_environment_update_usecase: AppDeploymentEnvironmentUpdateUseCase = Depends(
        AppDeploymentEnvironmentUpdateUseCase
    ),
):
    """App Deployment 환경 변수 설정 (ConfigMap upsert)

    App의 환경 변수를 설정합니다.
    - ConfigMap이 없으면 새로 생성합니다.
    - ConfigMap이 있으면 데이터를 완전히 교체합니다.
    """
    app_deployment_environment_update_result = (
        await app_deployment_environment_update_usecase(
            project_id=project_id,
            app_name=name,
            payload=payload,
        )
    )
    return SuccessResponse(
        message="App deployment environment variables updated successfully",
        data=app_deployment_environment_update_result,
    )


@app_router.delete(
    "/{project_id}/{name}/environment",
    response_model=SuccessResponse[EnvironmentDeleteResponse],
)
async def delete_app_deployment_environment(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_environment_delete_usecase: AppDeploymentEnvironmentDeleteUseCase = Depends(
        AppDeploymentEnvironmentDeleteUseCase
    ),
):
    """App Deployment 환경 변수 삭제 (ConfigMap 삭제)

    App의 환경 변수 ConfigMap을 삭제합니다.
    - ConfigMap이 존재하지 않으면 404 에러를 반환합니다.
    """
    app_deployment_environment_delete_result = (
        await app_deployment_environment_delete_usecase(
            project_id=project_id,
            app_name=name,
        )
    )
    return SuccessResponse(
        message="App deployment environment variables deleted successfully",
        data=app_deployment_environment_delete_result,
    )


@app_router.post(
    "/{project_id}/{name}/restart", response_model=SuccessResponse[AppRestartResponse]
)
async def restart_app_deployment(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_deployment_restart_usecase: AppDeploymentRestartUseCase = Depends(
        AppDeploymentRestartUseCase
    ),
):
    """App Deployment 재시작 (Rollout Restart)

    Deployment를 롤링 재시작합니다.
    - kubectl rollout restart 와 동일하게 동작합니다.
    - Pod 템플릿 어노테이션에 restartedAt 타임스탬프를 패치하여 롤링 업데이트를 트리거합니다.
    - 기존 Pod는 순서대로 교체되므로 서비스 중단 없이 재시작됩니다.
    """
    result = await app_deployment_restart_usecase(
        app_name=name,
        project_id=project_id,
    )
    return SuccessResponse(
        message="App deployment restart triggered successfully",
        data=AppRestartResponse(
            name=result["name"],
            namespace=result["namespace"],
            restarted_at=result["restarted_at"],
        ),
    )
