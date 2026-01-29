"""Kubernetes Namespace 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.namespace.schema import (
    NamespaceInfo,
    NamespaceListResponse,
    NamespaceDetailResponse,
)
from src.core.kubernetes.namespace import NamespaceRepository
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_namespace_repository

namespace_router = APIRouter(
    prefix="/namespaces",
    tags=["kubernetes-namespace"],
)


@namespace_router.get("", response_model=SuccessResponse[NamespaceListResponse])
async def list_namespaces(
    label_selector: Optional[str] = Query(
        default=None,
        description="Label selector (e.g., 'madp.io/name=myproject')",
    ),
    namespace_repo: NamespaceRepository = Depends(get_namespace_repository),
):
    """Kubernetes Namespace 목록 조회"""
    namespaces = await namespace_repo.find_all(label_selector=label_selector)

    namespace_infos = [
        NamespaceInfo(
            name=ns.id,
            status=ns.status,
            labels=ns.labels,
            annotations=ns.annotations,
        )
        for ns in namespaces
    ]

    return SuccessResponse(
        message="Namespaces retrieved successfully",
        data=NamespaceListResponse(
            namespaces=namespace_infos,
            total=len(namespace_infos),
        ),
    )


@namespace_router.get("/{name}", response_model=SuccessResponse[NamespaceDetailResponse])
async def get_namespace(
    name: str,
    namespace_repo: NamespaceRepository = Depends(get_namespace_repository),
):
    """특정 Namespace 상세 조회"""
    namespace = await namespace_repo.find_by_id(name)

    if namespace is None:
        raise HTTPException(status_code=404, detail=f"Namespace '{name}' not found")

    namespace_info = NamespaceInfo(
        name=namespace.id,
        status=namespace.status,
        labels=namespace.labels,
        annotations=namespace.annotations,
    )

    return SuccessResponse(
        message="Namespace retrieved successfully",
        data=NamespaceDetailResponse(namespace=namespace_info),
    )
