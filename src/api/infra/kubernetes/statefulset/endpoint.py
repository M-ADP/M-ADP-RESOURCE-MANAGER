"""Kubernetes StatefulSet 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.statefulset.schema import (
    StatefulSetStatusInfo,
    StatefulSetInfo,
    StatefulSetListResponse,
    StatefulSetDetailResponse,
)
from src.infra.kubernetes.managers.statefulset import StatefulSetManager
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_statefulset_manager

statefulset_router = APIRouter(
    prefix="/statefulsets",
    tags=["kubernetes-statefulset"],
)


@statefulset_router.get("", response_model=SuccessResponse[StatefulSetListResponse])
async def list_statefulsets(
    namespace: Optional[str] = Query(default=None, description="Filter by namespace"),
    label_selector: Optional[str] = Query(default=None, description="Label selector"),
    sts_manager: StatefulSetManager = Depends(get_statefulset_manager),
):
    """Kubernetes StatefulSet 목록 조회"""
    statefulsets = await sts_manager.list_statefulsets(
        namespace=namespace,
        label_selector=label_selector,
    )

    sts_infos = [
        StatefulSetInfo(
            name=sts.metadata.name,
            namespace=sts.metadata.namespace,
            replicas=sts.spec.replicas if sts.spec else 0,
            service_name=sts.spec.service_name if sts.spec else None,
            labels=sts.metadata.labels or {},
            annotations=sts.metadata.annotations or {},
            status=StatefulSetStatusInfo(
                replicas=sts.status.replicas,
                ready_replicas=sts.status.ready_replicas,
                current_replicas=sts.status.current_replicas,
                updated_replicas=sts.status.updated_replicas,
            ) if sts.status else None,
        )
        for sts in statefulsets
    ]

    return SuccessResponse(
        message="StatefulSets retrieved successfully",
        data=StatefulSetListResponse(statefulsets=sts_infos, total=len(sts_infos)),
    )


@statefulset_router.get("/{namespace}/{name}", response_model=SuccessResponse[StatefulSetDetailResponse])
async def get_statefulset(
    namespace: str,
    name: str,
    sts_manager: StatefulSetManager = Depends(get_statefulset_manager),
):
    """특정 StatefulSet 상세 조회"""
    sts = await sts_manager.get_statefulset(name, namespace)

    if sts is None:
        raise HTTPException(status_code=404, detail=f"StatefulSet '{name}' not found in namespace '{namespace}'")

    sts_info = StatefulSetInfo(
        name=sts.metadata.name,
        namespace=sts.metadata.namespace,
        replicas=sts.spec.replicas if sts.spec else 0,
        service_name=sts.spec.service_name if sts.spec else None,
        labels=sts.metadata.labels or {},
        annotations=sts.metadata.annotations or {},
        status=StatefulSetStatusInfo(
            replicas=sts.status.replicas,
            ready_replicas=sts.status.ready_replicas,
            current_replicas=sts.status.current_replicas,
            updated_replicas=sts.status.updated_replicas,
        ) if sts.status else None,
    )

    return SuccessResponse(
        message="StatefulSet retrieved successfully",
        data=StatefulSetDetailResponse(statefulset=sts_info),
    )
