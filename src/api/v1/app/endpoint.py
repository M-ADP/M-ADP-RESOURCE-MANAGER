"""App API 라우터"""

from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, Path, Query

from src.api.v1.app.schemas.request import (
    AppCreateRequest,
    AppRevisionRequest,
    AutoScaleRequest,
    FixedScaleRequest,
    SecretCreateRequest,
    EnvironmentUpdateRequest,
    SecurityContextPatchRequest,
)
from src.api.v1.app.schemas.response import (
    AppCreateResponse,
    AppDeleteResponse,
    AppRevisionResponse,
    AutoScaleResponse,
    FixedScaleResponse,
    SecretCreateResponse,
    SecretDeleteResponse,
    SecretKeyDeleteResponse,
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

from src.api.v1.app.schemas.security_response import (
    AppSecurityConfigResponse,
    AppVulnerabilityResponse,
    AppPodKillResponse,
    AppSecurityContextPatchResponse,
    AppSecurityAuditResponse,
)
from src.app.app_deployment.app_security_events_use_case import (
    AppSecurityEventsUseCase,
)
from src.app.app_deployment.app_security_config_use_case import (
    AppSecurityConfigUseCase,
)
from src.app.app_deployment.app_security_vulnerabilities_use_case import (
    AppSecurityVulnerabilitiesUseCase,
)
from src.app.app_deployment.app_pod_kill_use_case import AppPodKillUseCase
from src.app.app_deployment.app_security_context_patch_use_case import (
    AppSecurityContextPatchUseCase,
)
from src.app.app_deployment.app_security_audit_use_case import AppSecurityAuditUseCase

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
    timestamps: bool = Query(default=True, description="타임스탬프 포함 여부"),
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
async def get_apps_resource_status(
    project_id: str = Path(..., description="프로젝트 ID"),
    names: Annotated[List[str], Query(description="App 이름 목록")] = [],
    app_resource_status_usecase: AppResourceStatusUseCase = Depends(
        AppResourceStatusUseCase
    ),
):
    """App 리소스 상태 일괄 조회

    여러 Deployment의 리소스 상태를 한 번에 조회합니다.
    존재하지 않는 앱은 결과에서 제외됩니다.
    """
    result = await app_resource_status_usecase(
        project_id=project_id,
        app_ids=names,
    )
    return SuccessResponse(
        message="App resource status retrieved successfully",
        data=result,
    )


@app_router.get(
    "/{project_id}/{name}/resource-status",
    response_model=SuccessResponse[AppResourceStatusResponse],
)
async def get_app_resource_status(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름 (Deployment 이름)"),
    app_resource_status_usecase: AppResourceStatusUseCase = Depends(
        AppResourceStatusUseCase
    ),
):
    """App 리소스 상태 조회

    Deployment의 CPU, Memory 사용량 정보를 조회합니다.
    """
    results = await app_resource_status_usecase(
        project_id=project_id,
        app_ids=[name],
    )
    return SuccessResponse(
        message="App resource status retrieved successfully",
        data=results[0] if results else None,
    )


@app_router.post(
    "/{project_id}/{name}/autoscale", response_model=SuccessResponse[AutoScaleResponse]
)
async def update_app_autoscale(
    payload: AutoScaleRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    app_deployment_autoscale_usecase: AppDeploymentAutoScaleUseCase = Depends(
        AppDeploymentAutoScaleUseCase
    ),
):
    """App 오토스케일링 설정

    HPA(Horizontal Pod Autoscaler)를 생성하거나 수정합니다.
    """
    result = await app_deployment_autoscale_usecase(
        project_id=project_id,
        app_name=name,
        payload=payload,
    )
    return SuccessResponse(
        message="App autoscale updated successfully",
        data=result,
    )


@app_router.post(
    "/{project_id}/{name}/fixedscale",
    response_model=SuccessResponse[FixedScaleResponse],
)
async def update_app_fixedscale(
    payload: FixedScaleRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    app_deployment_fixed_scale_usecase: AppDeploymentFixedScaleUseCase = Depends(
        AppDeploymentFixedScaleUseCase
    ),
):
    """App 고정 스케일링 설정

    HPA를 제거하고 고정된 레플리카 수를 설정합니다.
    """
    result = await app_deployment_fixed_scale_usecase(
        project_id=project_id,
        app_name=name,
        payload=payload,
    )
    return SuccessResponse(
        message="App fixed scale updated successfully",
        data=result,
    )


@app_router.post(
    "/{project_id}/{name}/secrets", response_model=SuccessResponse[SecretCreateResponse]
)
async def create_app_secret(
    payload: SecretCreateRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    app_deployment_secret_create_usecase: AppDeploymentSecretCreateUseCase = Depends(
        AppDeploymentSecretCreateUseCase
    ),
):
    """App Secret 생성

    Vault와 Kubernetes Secret에 민감 정보를 저장합니다.
    """
    result = await app_deployment_secret_create_usecase(
        project_id=project_id,
        app_name=name,
        payload=payload,
    )
    return SuccessResponse(
        message="App secret created successfully",
        data=result,
    )


@app_router.delete(
    "/{project_id}/{name}/secrets/{key}",
    response_model=SuccessResponse[SecretKeyDeleteResponse],
)
async def delete_app_secret(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    key: str = Path(..., description="Secret 키"),
    app_deployment_secret_delete_usecase: AppDeploymentSecretDeleteUseCase = Depends(
        AppDeploymentSecretDeleteUseCase
    ),
):
    """App Secret 키 단위 삭제

    Vault에서 특정 키만 제거하고 나머지 키는 유지합니다.
    """
    result = await app_deployment_secret_delete_usecase(
        project_id=project_id,
        app_name=name,
        key=key,
    )
    return SuccessResponse(
        message="App secret key deleted successfully",
        data=result,
    )


@app_router.put(
    "/{project_id}/{name}/environments",
    response_model=SuccessResponse[EnvironmentUpdateResponse],
)
async def update_app_environments(
    payload: EnvironmentUpdateRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    app_deployment_environment_update_usecase: AppDeploymentEnvironmentUpdateUseCase = Depends(
        AppDeploymentEnvironmentUpdateUseCase
    ),
):
    """App 환경 변수 설정

    Deployment의 환경 변수를 설정합니다. (기존 환경 변수는 유지되거나 업데이트됨)
    """
    result = await app_deployment_environment_update_usecase(
        project_id=project_id,
        app_name=name,
        payload=payload,
    )
    return SuccessResponse(
        message="App environments updated successfully",
        data=result,
    )


@app_router.delete(
    "/{project_id}/{name}/environments/{key}",
    response_model=SuccessResponse[EnvironmentDeleteResponse],
)
async def delete_app_environment(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    key: str = Path(..., description="환경 변수 키"),
    app_deployment_environment_delete_usecase: AppDeploymentEnvironmentDeleteUseCase = Depends(
        AppDeploymentEnvironmentDeleteUseCase
    ),
):
    """App 환경 변수 삭제

    Deployment의 특정 환경 변수를 삭제합니다.
    """
    result = await app_deployment_environment_delete_usecase(
        project_id=project_id,
        app_name=name,
        key=key,
    )
    return SuccessResponse(
        message="App environment deleted successfully",
        data=result,
    )


@app_router.post(
    "/{project_id}/{name}/restart",
    response_model=SuccessResponse[AppRestartResponse],
)
async def restart_app_deployment(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    app_deployment_restart_usecase: AppDeploymentRestartUseCase = Depends(
        AppDeploymentRestartUseCase
    ),
):
    """App 재시작

    Deployment를 재시작(Rollout Restart)합니다.
    """
    result = await app_deployment_restart_usecase(
        project_id=project_id,
        app_name=name,
    )
    return SuccessResponse(
        message="App deployment restarted successfully",
        data=result,
    )


@app_router.post(
    "/{project_id}/{name}/pods/{pod_name}/kill",
    response_model=SuccessResponse[AppPodKillResponse],
)
async def kill_app_pod(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    pod_name: str = Path(..., description="종료할 Pod 이름"),
    use_case: AppPodKillUseCase = Depends(AppPodKillUseCase),
):
    """특정 Pod 강제 종료

    Deployment 소속 Pod를 강제 종료합니다. Deployment 컨트롤러가 자동으로 새 Pod를 생성합니다.
    """
    result = await use_case(app_name=name, project_id=project_id, pod_name=pod_name)
    return SuccessResponse(message="Pod killed successfully", data=result)


@app_router.patch(
    "/{project_id}/{name}/security/context",
    response_model=SuccessResponse[AppSecurityContextPatchResponse],
)
async def patch_app_security_context(
    payload: SecurityContextPatchRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    use_case: AppSecurityContextPatchUseCase = Depends(AppSecurityContextPatchUseCase),
):
    """App 보안 컨텍스트 패치

    Deployment 전체 컨테이너의 securityContext를 강제 적용합니다.
    None 필드는 변경하지 않습니다.
    """
    result = await use_case(
        app_name=name,
        project_id=project_id,
        run_as_non_root=payload.run_as_non_root,
        allow_privilege_escalation=payload.allow_privilege_escalation,
        read_only_root_filesystem=payload.read_only_root_filesystem,
        privileged=payload.privileged,
        capabilities_drop=payload.capabilities_drop,
    )
    return SuccessResponse(message="Security context patched successfully", data=result)


@app_router.post(
    "/{project_id}/{name}/security/audit",
    response_model=SuccessResponse[AppSecurityAuditResponse],
)
async def audit_app_security(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    use_case: AppSecurityAuditUseCase = Depends(AppSecurityAuditUseCase),
):
    """App 보안 감사 (읽기 전용)

    현재 securityContext를 보안 정책 기준으로 검증합니다.
    CRITICAL/HIGH 항목이 있으면 passed=false를 반환합니다.
    """
    result = await use_case(app_name=name, project_id=project_id)
    return SuccessResponse(message="Security audit completed", data=result)


@app_router.get(
    "/{project_id}/{name}/security/events",
    response_model=SuccessResponse[AppEventsResponse],
)
async def get_app_security_events(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    since_seconds: int = Query(default=60, description="조회할 시간 범위(초)"),
    use_case: AppSecurityEventsUseCase = Depends(AppSecurityEventsUseCase),
):
    """App 보안 관련 최근 이벤트 조회 (RuntimeSecurityAgent)"""
    result = await use_case(app_name=name, project_id=project_id, since_seconds=since_seconds)
    return SuccessResponse(message="Security events retrieved successfully", data=result)


@app_router.get(
    "/{project_id}/{name}/security/config",
    response_model=SuccessResponse[AppSecurityConfigResponse],
)
async def get_app_security_config(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    use_case: AppSecurityConfigUseCase = Depends(AppSecurityConfigUseCase),
):
    """App 보안 설정 및 리소스 조회 (ConfigSecurityAgent)"""
    result = await use_case(app_name=name, project_id=project_id)
    return SuccessResponse(message="Security config retrieved successfully", data=result)


@app_router.get(
    "/{project_id}/{name}/security/vulnerabilities",
    response_model=SuccessResponse[List[AppVulnerabilityResponse]],
)
async def get_app_vulnerabilities(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="App 이름"),
    use_case: AppSecurityVulnerabilitiesUseCase = Depends(AppSecurityVulnerabilitiesUseCase),
):
    """App 이미지 취약점 스캔 결과 조회 (ImageSecurityAgent)"""
    result = await use_case(app_name=name, project_id=project_id)
    return SuccessResponse(message="Vulnerabilities retrieved successfully", data=result)
