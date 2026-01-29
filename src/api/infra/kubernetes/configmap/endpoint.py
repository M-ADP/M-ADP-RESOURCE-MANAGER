"""Kubernetes ConfigMap 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.configmap.schema import (
    ConfigMapInfo,
    ConfigMapListResponse,
    ConfigMapDetailResponse,
)
from src.infra.kubernetes.managers.configmap import ConfigMapManager
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_configmap_manager

configmap_router = APIRouter(
    prefix="/configmaps",
    tags=["kubernetes-configmap"],
)


@configmap_router.get("", response_model=SuccessResponse[ConfigMapListResponse])
async def list_configmaps(
    namespace: Optional[str] = Query(default=None, description="Filter by namespace"),
    label_selector: Optional[str] = Query(default=None, description="Label selector"),
    cm_manager: ConfigMapManager = Depends(get_configmap_manager),
):
    """Kubernetes ConfigMap 목록 조회"""
    configmaps = await cm_manager.list_configmaps(
        namespace=namespace,
        label_selector=label_selector,
    )

    cm_infos = [
        ConfigMapInfo(
            name=cm.metadata.name,
            namespace=cm.metadata.namespace,
            data=cm.data or {},
            labels=cm.metadata.labels or {},
            annotations=cm.metadata.annotations or {},
        )
        for cm in configmaps
    ]

    return SuccessResponse(
        message="ConfigMaps retrieved successfully",
        data=ConfigMapListResponse(configmaps=cm_infos, total=len(cm_infos)),
    )


@configmap_router.get("/{namespace}/{name}", response_model=SuccessResponse[ConfigMapDetailResponse])
async def get_configmap(
    namespace: str,
    name: str,
    cm_manager: ConfigMapManager = Depends(get_configmap_manager),
):
    """특정 ConfigMap 상세 조회"""
    cm = await cm_manager.get_configmap(name, namespace)

    if cm is None:
        raise HTTPException(status_code=404, detail=f"ConfigMap '{name}' not found in namespace '{namespace}'")

    cm_info = ConfigMapInfo(
        name=cm.metadata.name,
        namespace=cm.metadata.namespace,
        data=cm.data or {},
        labels=cm.metadata.labels or {},
        annotations=cm.metadata.annotations or {},
    )

    return SuccessResponse(
        message="ConfigMap retrieved successfully",
        data=ConfigMapDetailResponse(configmap=cm_info),
    )
