"""Kubernetes PersistentVolumeClaim 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.pvc.schema import (
    PVCInfo,
    PVCListResponse,
    PVCDetailResponse,
)
from src.infra.kubernetes.managers.persistentvolumeclaim import PersistentVolumeClaimManager
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_pvc_manager

pvc_router = APIRouter(
    prefix="/pvcs",
    tags=["kubernetes-pvc"],
)


@pvc_router.get("", response_model=SuccessResponse[PVCListResponse])
async def list_pvcs(
    namespace: Optional[str] = Query(default=None, description="Filter by namespace"),
    label_selector: Optional[str] = Query(default=None, description="Label selector"),
    pvc_manager: PersistentVolumeClaimManager = Depends(get_pvc_manager),
):
    """Kubernetes PersistentVolumeClaim 목록 조회"""
    pvcs = await pvc_manager.list_pvcs(
        namespace=namespace,
        label_selector=label_selector,
    )

    pvc_infos = [
        PVCInfo(
            name=pvc.metadata.name,
            namespace=pvc.metadata.namespace,
            storage_class=pvc.spec.storage_class_name if pvc.spec else None,
            access_modes=pvc.spec.access_modes if pvc.spec else [],
            capacity=pvc.status.capacity.get("storage") if pvc.status and pvc.status.capacity else None,
            requested_storage=pvc.spec.resources.requests.get("storage") if pvc.spec and pvc.spec.resources and pvc.spec.resources.requests else None,
            phase=pvc.status.phase if pvc.status else None,
            volume_name=pvc.spec.volume_name if pvc.spec else None,
            labels=pvc.metadata.labels or {},
            annotations=pvc.metadata.annotations or {},
        )
        for pvc in pvcs
    ]

    return SuccessResponse(
        message="PVCs retrieved successfully",
        data=PVCListResponse(pvcs=pvc_infos, total=len(pvc_infos)),
    )


@pvc_router.get("/{namespace}/{name}", response_model=SuccessResponse[PVCDetailResponse])
async def get_pvc(
    namespace: str,
    name: str,
    pvc_manager: PersistentVolumeClaimManager = Depends(get_pvc_manager),
):
    """특정 PVC 상세 조회"""
    pvc = await pvc_manager.get_pvc(name, namespace)

    if pvc is None:
        raise HTTPException(status_code=404, detail=f"PVC '{name}' not found in namespace '{namespace}'")

    pvc_info = PVCInfo(
        name=pvc.metadata.name,
        namespace=pvc.metadata.namespace,
        storage_class=pvc.spec.storage_class_name if pvc.spec else None,
        access_modes=pvc.spec.access_modes if pvc.spec else [],
        capacity=pvc.status.capacity.get("storage") if pvc.status and pvc.status.capacity else None,
        requested_storage=pvc.spec.resources.requests.get("storage") if pvc.spec and pvc.spec.resources and pvc.spec.resources.requests else None,
        phase=pvc.status.phase if pvc.status else None,
        volume_name=pvc.spec.volume_name if pvc.spec else None,
        labels=pvc.metadata.labels or {},
        annotations=pvc.metadata.annotations or {},
    )

    return SuccessResponse(
        message="PVC retrieved successfully",
        data=PVCDetailResponse(pvc=pvc_info),
    )
