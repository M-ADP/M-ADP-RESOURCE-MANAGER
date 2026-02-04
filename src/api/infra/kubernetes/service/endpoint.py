"""Kubernetes Service 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.service.schema import (
    ServicePortInfo,
    ServiceInfo,
    ServiceListResponse,
    ServiceDetailResponse,
)
from src.core.kubernetes.service import ServiceRepository
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_service_repository

service_router = APIRouter(
    prefix="/services",
    tags=["kubernetes-service"],
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
    service_repo: ServiceRepository = Depends(get_service_repository),
):
    """Kubernetes Service 목록 조회"""
    services = await service_repo.find_all(
        namespace=namespace,
        label_selector=label_selector,
    )

    service_infos = [
        ServiceInfo(
            name=svc.id,
            namespace=svc.namespace,
            ports=[
                ServicePortInfo(
                    port=p.port,
                    target_port=p.target_port,
                    protocol=p.protocol,
                    name=p.name,
                    node_port=p.node_port,
                )
                for p in svc.ports
            ],
            selector=svc.selector,
            service_type=svc.service_type,
            labels=svc.labels,
            annotations=svc.annotations,
            cluster_ip=svc.cluster_ip,
            external_ips=svc.external_ips,
        )
        for svc in services
    ]

    return SuccessResponse(
        message="Services retrieved successfully",
        data=ServiceListResponse(
            services=service_infos,
            total=len(service_infos),
        ),
    )


@service_router.get("/{namespace}/{name}", response_model=SuccessResponse[ServiceDetailResponse])
async def get_service(
    namespace: str,
    name: str,
    service_repo: ServiceRepository = Depends(get_service_repository),
):
    """특정 Service 상세 조회"""
    service = await service_repo.find_by_id(name, namespace)

    if service is None:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{name}' not found in namespace '{namespace}'",
        )

    service_info = ServiceInfo(
        name=service.id,
        namespace=service.namespace,
        ports=[
            ServicePortInfo(
                port=p.port,
                target_port=p.target_port,
                protocol=p.protocol,
                name=p.name,
                node_port=p.node_port,
            )
            for p in service.ports
        ],
        selector=service.selector,
        service_type=service.service_type,
        labels=service.labels,
        annotations=service.annotations,
        cluster_ip=service.cluster_ip,
        external_ips=service.external_ips,
    )

    return SuccessResponse(
        message="Service retrieved successfully",
        data=ServiceDetailResponse(service=service_info),
    )
