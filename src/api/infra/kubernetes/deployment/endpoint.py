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
from src.core.kubernetes.deployment import DeploymentRepository
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_deployment_repository

deployment_router = APIRouter(
    prefix="/deployments",
    tags=["kubernetes-deployment"],
)


@deployment_router.get("", response_model=SuccessResponse[DeploymentListResponse])
async def list_deployments(
    namespace: Optional[str] = Query(
        default=None,
        description="Filter by namespace",
    ),
    label_selector: Optional[str] = Query(
        default=None,
        description="Label selector (e.g., 'app=myapp')",
    ),
    deployment_repo: DeploymentRepository = Depends(get_deployment_repository),
):
    """Kubernetes Deployment 목록 조회"""
    deployments = await deployment_repo.find_all(
        namespace=namespace,
        label_selector=label_selector,
    )

    deployment_infos = [
        DeploymentInfo(
            name=dep.name,
            namespace=dep.namespace,
            replicas=dep.replicas,
            containers=[
                ContainerInfo(name=c.name, image=c.image)
                for c in dep.containers
            ],
            labels=dep.labels,
            annotations=dep.annotations,
            selector_labels=dep.selector_labels,
            status=DeploymentStatusInfo(
                replicas=dep.status.replicas,
                ready_replicas=dep.status.ready_replicas,
                available_replicas=dep.status.available_replicas,
                updated_replicas=dep.status.updated_replicas,
            ) if dep.status else None,
        )
        for dep in deployments
    ]

    return SuccessResponse(
        message="Deployments retrieved successfully",
        data=DeploymentListResponse(
            deployments=deployment_infos,
            total=len(deployment_infos),
        ),
    )


@deployment_router.get("/{namespace}/{name}", response_model=SuccessResponse[DeploymentDetailResponse])
async def get_deployment(
    namespace: str,
    name: str,
    deployment_repo: DeploymentRepository = Depends(get_deployment_repository),
):
    """특정 Deployment 상세 조회"""
    deployment = await deployment_repo.find_by_name(name, namespace)

    if deployment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment '{name}' not found in namespace '{namespace}'",
        )

    deployment_info = DeploymentInfo(
        name=deployment.name,
        namespace=deployment.namespace,
        replicas=deployment.replicas,
        containers=[
            ContainerInfo(name=c.name, image=c.image)
            for c in deployment.containers
        ],
        labels=deployment.labels,
        annotations=deployment.annotations,
        selector_labels=deployment.selector_labels,
        status=DeploymentStatusInfo(
            replicas=deployment.status.replicas,
            ready_replicas=deployment.status.ready_replicas,
            available_replicas=deployment.status.available_replicas,
            updated_replicas=deployment.status.updated_replicas,
        ) if deployment.status else None,
    )

    return SuccessResponse(
        message="Deployment retrieved successfully",
        data=DeploymentDetailResponse(deployment=deployment_info),
    )
