"""Kubernetes Deployment 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.deployment.schema import (
    ContainerInfo,
    DeploymentStatusInfo,
    DeploymentInfo,
    DeploymentListResponse,
    DeploymentDetailResponse,
)
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_deployment_manager
from src.infra.kubernetes.managers.deployment import DeploymentManager

deployment_router = APIRouter(
    prefix="/deployments",
    tags=["kubernetes-deployment"],
)


def _build_deployment_info(dep) -> DeploymentInfo:
    containers = []
    if dep.spec and dep.spec.template and dep.spec.template.spec:
        containers = [
            ContainerInfo(name=c.name, image=c.image)
            for c in dep.spec.template.spec.containers or []
        ]

    status = None
    if dep.status:
        status = DeploymentStatusInfo(
            replicas=dep.status.replicas,
            ready_replicas=dep.status.ready_replicas,
            available_replicas=dep.status.available_replicas,
            updated_replicas=dep.status.updated_replicas,
        )

    return DeploymentInfo(
        name=dep.metadata.name,
        namespace=dep.metadata.namespace,
        replicas=dep.spec.replicas if dep.spec else 1,
        containers=containers,
        labels=dep.metadata.labels or {},
        annotations=dep.metadata.annotations or {},
        selector_labels=dep.spec.selector.match_labels if dep.spec and dep.spec.selector else {},
        status=status,
    )


@deployment_router.get("", response_model=SuccessResponse[DeploymentListResponse])
async def list_deployments(
    namespace: Optional[str] = Query(
        default=None,
        description="Filter by namespace",
    ),
    label_selector: Optional[str] = Query(
        default=None,
        description="Label selector (e.g., 'app_deployment=myapp')",
    ),
    deployment_manager: DeploymentManager = Depends(get_deployment_manager),
):
    """Kubernetes Deployment 목록 조회"""
    deployments = await deployment_manager.list_deployments(
        namespace=namespace,
        label_selector=label_selector,
    )

    return SuccessResponse(
        message="Deployments retrieved successfully",
        data=DeploymentListResponse(
            deployments=[_build_deployment_info(dep) for dep in deployments],
            total=len(deployments),
        ),
    )


@deployment_router.get("/{namespace}/{name}", response_model=SuccessResponse[DeploymentDetailResponse])
async def get_deployment(
    namespace: str,
    name: str,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager),
):
    """특정 Deployment 상세 조회"""
    dep = await deployment_manager.get_deployment(name, namespace)

    if dep is None:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment '{name}' not found in namespace '{namespace}'",
        )

    return SuccessResponse(
        message="Deployment retrieved successfully",
        data=DeploymentDetailResponse(deployment=_build_deployment_info(dep)),
    )
