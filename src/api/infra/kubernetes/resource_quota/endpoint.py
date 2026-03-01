"""Kubernetes ResourceQuota 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.resource_quota.schema import (
    ResourceQuotaInfo,
    ResourceQuotaListResponse,
    ResourceQuotaDetailResponse,
)
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_resource_quota_manager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager

resource_quota_router = APIRouter(
    prefix="/resource-quotas",
    tags=["kubernetes-resource-quota"],
)


@resource_quota_router.get("", response_model=SuccessResponse[ResourceQuotaListResponse])
async def list_resource_quotas(
    namespace: Optional[str] = Query(
        default=None,
        description="Filter by namespace",
    ),
    label_selector: Optional[str] = Query(
        default=None,
        description="Label selector (e.g., 'madp.io/name=myproject')",
    ),
    rq_manager: ResourceQuotaManager = Depends(get_resource_quota_manager),
):
    """Kubernetes ResourceQuota 목록 조회"""
    quotas = await rq_manager.list_resource_quotas(
        namespace=namespace,
        label_selector=label_selector,
    )

    quota_infos = [
        ResourceQuotaInfo(
            name=rq.metadata.name,
            namespace=rq.metadata.namespace,
            hard_limits=rq.spec.hard if rq.spec and rq.spec.hard else {},
            used=rq.status.used if rq.status and rq.status.used else {},
            labels=rq.metadata.labels or {},
            annotations=rq.metadata.annotations or {},
        )
        for rq in quotas
    ]

    return SuccessResponse(
        message="ResourceQuotas retrieved successfully",
        data=ResourceQuotaListResponse(
            resource_quotas=quota_infos,
            total=len(quota_infos),
        ),
    )


@resource_quota_router.get("/{namespace}/{name}", response_model=SuccessResponse[ResourceQuotaDetailResponse])
async def get_resource_quota(
    namespace: str,
    name: str,
    rq_manager: ResourceQuotaManager = Depends(get_resource_quota_manager),
):
    """특정 ResourceQuota 상세 조회"""
    rq = await rq_manager.get_resource_quota(name, namespace)

    if rq is None:
        raise HTTPException(
            status_code=404,
            detail=f"ResourceQuota '{name}' not found in namespace '{namespace}'",
        )

    quota_info = ResourceQuotaInfo(
        name=rq.metadata.name,
        namespace=rq.metadata.namespace,
        hard_limits=rq.spec.hard if rq.spec and rq.spec.hard else {},
        used=rq.status.used if rq.status and rq.status.used else {},
        labels=rq.metadata.labels or {},
        annotations=rq.metadata.annotations or {},
    )

    return SuccessResponse(
        message="ResourceQuota retrieved successfully",
        data=ResourceQuotaDetailResponse(resource_quota=quota_info),
    )
