"""Kubernetes ResourceQuota 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.resource_quota.schema import (
    ResourceQuotaInfo,
    ResourceQuotaListResponse,
    ResourceQuotaDetailResponse,
)
from src.core.kubernetes.resource_quota import ResourceQuotaRepository
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_resource_quota_repository

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
    rq_repo: ResourceQuotaRepository = Depends(get_resource_quota_repository),
):
    """Kubernetes ResourceQuota 목록 조회"""
    quotas = await rq_repo.find_all(
        namespace=namespace,
        label_selector=label_selector,
    )

    quota_infos = [
        ResourceQuotaInfo(
            name=rq.id,
            namespace=rq.namespace,
            hard_limits=rq.hard_limits,
            used=rq.used,
            labels=rq.labels,
            annotations=rq.annotations,
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
    rq_repo: ResourceQuotaRepository = Depends(get_resource_quota_repository),
):
    """특정 ResourceQuota 상세 조회"""
    quota = await rq_repo.find_by_id(name, namespace)

    if quota is None:
        raise HTTPException(
            status_code=404,
            detail=f"ResourceQuota '{name}' not found in namespace '{namespace}'",
        )

    quota_info = ResourceQuotaInfo(
        name=quota.id,
        namespace=quota.namespace,
        hard_limits=quota.hard_limits,
        used=quota.used,
        labels=quota.labels,
        annotations=quota.annotations,
    )

    return SuccessResponse(
        message="ResourceQuota retrieved successfully",
        data=ResourceQuotaDetailResponse(resource_quota=quota_info),
    )
