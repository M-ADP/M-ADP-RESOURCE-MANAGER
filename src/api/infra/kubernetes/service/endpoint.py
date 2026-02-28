"""Kubernetes Service 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.service.schema import (
    ServicePortInfo,
    ServiceInfo,
    ServiceListResponse,
    ServiceDetailResponse,
)
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_service_manager
from src.infra.kubernetes.managers.service import ServiceManager

service_router = APIRouter(
    prefix="/services",
    tags=["kubernetes-service"],
)


def _build_service_info(svc) -> ServiceInfo:
    ports = []
    if svc.spec and svc.spec.ports:
        for p in svc.spec.ports:
            target_port = p.target_port if isinstance(p.target_port, int) else int(p.target_port) if p.target_port else None
            ports.append(ServicePortInfo(
                port=p.port,
                target_port=target_port,
                protocol=p.protocol,
                name=p.name,
                node_port=p.node_port,
            ))

    return ServiceInfo(
        name=svc.metadata.name,
        namespace=svc.metadata.namespace,
        ports=ports,
        selector=svc.spec.selector if svc.spec else {},
        service_type=svc.spec.type if svc.spec else "ClusterIP",
        labels=svc.metadata.labels or {},
        annotations=svc.metadata.annotations or {},
        cluster_ip=svc.spec.cluster_ip if svc.spec else None,
        external_ips=svc.spec.external_ips if svc.spec and svc.spec.external_ips else [],
    )


@service_router.get("", response_model=SuccessResponse[ServiceListResponse])
async def list_services(
    namespace: Optional[str] = Query(
        default=None,
        description="Filter by namespace",
    ),
    label_selector: Optional[str] = Query(
        default=None,
        description="Label selector (e.g., 'app_deployment=myapp')",
    ),
    service_manager: ServiceManager = Depends(get_service_manager),
):
    """Kubernetes Service 목록 조회"""
    services = await service_manager.list_services(
        namespace=namespace,
        label_selector=label_selector,
    )

    return SuccessResponse(
        message="Services retrieved successfully",
        data=ServiceListResponse(
            services=[_build_service_info(svc) for svc in services],
            total=len(services),
        ),
    )


@service_router.get("/{namespace}/{name}", response_model=SuccessResponse[ServiceDetailResponse])
async def get_service(
    namespace: str,
    name: str,
    service_manager: ServiceManager = Depends(get_service_manager),
):
    """특정 Service 상세 조회"""
    svc = await service_manager.get_service(name, namespace)

    if svc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{name}' not found in namespace '{namespace}'",
        )

    return SuccessResponse(
        message="Service retrieved successfully",
        data=ServiceDetailResponse(service=_build_service_info(svc)),
    )
