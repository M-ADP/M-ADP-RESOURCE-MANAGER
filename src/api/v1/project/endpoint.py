"""Project API 라우터"""

from fastapi import APIRouter, Depends

from src.api.v1.deps.user import get_user
from src.api.v1.project.schmas.request import (
    ProjectCreateRequest, ProjectPortOpenRequest, ProjectPortUpdateRequest, ProjectDnsCreateRequest,
    ProjectDnsUpdateRequest, ProjectDnsPortBindRequest, ProjectResourceUpdateRequest,
)
from src.api.v1.project.schmas.response import (
    ProjectCreateResponse, ProjectDeleteResponse, ProjectPortOpenResponse, ServicePortResponse, ProjectPortCloseResponse,
    ProjectPortUpdateResponse, ProjectDnsCreateResponse, ProjectDnsDeleteResponse, ProjectDnsUpdateResponse,
    ProjectDnsPortBindResponse, ProjectResourceUpdateResponse,
)
from src.app.project.project_create_use_case import ProjectCreateUseCase
from src.app.project.project_delete_use_case import ProjectDeleteUseCase
from src.app.project.project_port_open_use_case import ProjectPortOpenUseCase
from src.app.project.project_port_close_use_case import ProjectPortCloseUseCase
from src.app.project.project_port_update_use_case import ProjectPortUpdateUseCase
from src.app.project.project_dns_create_use_case import ProjectDnsCreateUseCase
from src.app.project.project_dns_delete_use_case import ProjectDnsDeleteUseCase
from src.app.project.project_dns_update_use_case import ProjectDnsUpdateUseCase
from src.app.project.project_dns_port_bind_use_case import ProjectDnsPortBindUseCase
from src.app.project.project_resource_update_use_case import ProjectResourceUpdateUseCase
from src.app.monitoring.project_resource_status_use_case import ProjectResourceStatusUseCase
from src.app.monitoring.dto import ProjectResourceStatusResponse
from src.core.response import SuccessResponse
from src.core.user.model import User

project_router = APIRouter(prefix="/projects", tags=["projects"])


@project_router.get("/{name}/resource", response_model=SuccessResponse[ProjectResourceStatusResponse])
async def get_project_resources(
    name: str,
    user: User = Depends(get_user),
    project_resource_status_usecase: ProjectResourceStatusUseCase = Depends(ProjectResourceStatusUseCase)
):
    resource_status = await project_resource_status_usecase(
        project_id=name
    )
    return SuccessResponse(
        message="Project resource status retrieved successfully",
        data=resource_status
    )


@project_router.post("", response_model=SuccessResponse[ProjectCreateResponse])
async def create_project(
    payload: ProjectCreateRequest,
    user: User = Depends(get_user),
    project_create_usecase : ProjectCreateUseCase = Depends(ProjectCreateUseCase)
):
    project_create_result = await project_create_usecase(
        payload,
        user.id
    )
    return SuccessResponse(
        message="Project created",
        data=project_create_result
    )


@project_router.delete("/{name}", response_model=SuccessResponse[ProjectDeleteResponse])
async def delete_project(
    name: str,
    user: User = Depends(get_user),
    project_delete_usecase : ProjectDeleteUseCase = Depends(ProjectDeleteUseCase)
):
    project_delete_result = await project_delete_usecase(
        name,
        user.id
    )
    return SuccessResponse(
        message="Project deleted",
        data=project_delete_result,
    )


@project_router.post("/{name}/ports", response_model=SuccessResponse[ProjectPortOpenResponse])
async def open_project_port(
    name: str,
    payload: ProjectPortOpenRequest,
    user: User = Depends(get_user),
    project_port_open_usecase: ProjectPortOpenUseCase = Depends(ProjectPortOpenUseCase)
):
    service = await project_port_open_usecase(
        project_id=name,
        payload=payload
    )

    ports_response = [
        ServicePortResponse(
            port=p.port,
            target_port=p.target_port,
            protocol=p.protocol,
            name=p.name,
            node_port=p.node_port
        ) for p in service.ports
    ]

    response = ProjectPortOpenResponse(
        name=service.name,
        namespace=service.namespace,
        ports=ports_response,
        selector=service.selector,
        service_type=service.service_type,
        cluster_ip=service.cluster_ip,
        external_ips=service.external_ips
    )

    return SuccessResponse(
        message="Port opened successfully",
        data=response
    )


@project_router.put("/{name}/ports/{port_id}", response_model=SuccessResponse[ProjectPortUpdateResponse])
async def update_project_port(
    name: str,
    port_id: int,  # path parameter (하위 호환성 유지, 실제로는 사용하지 않음)
    payload: ProjectPortUpdateRequest,
    user: User = Depends(get_user),
    project_port_update_usecase: ProjectPortUpdateUseCase = Depends(ProjectPortUpdateUseCase)
):
    # service_id로 Service를 찾아 업데이트 (port_id는 사용하지 않음)
    service = await project_port_update_usecase(
        project_id=name,
        payload=payload
    )

    ports_response = [
        ServicePortResponse(
            port=p.port,
            target_port=p.target_port,
            protocol=p.protocol,
            name=p.name,
            node_port=p.node_port
        ) for p in service.ports
    ]

    response = ProjectPortUpdateResponse(
        name=service.name,
        namespace=service.namespace,
        ports=ports_response,
        selector=service.selector,
        service_type=service.service_type,
        cluster_ip=service.cluster_ip,
        external_ips=service.external_ips
    )

    return SuccessResponse(
        message="Port updated successfully",
        data=response
    )


@project_router.delete("/{name}/ports/{port_id}", response_model=SuccessResponse[ProjectPortCloseResponse])
async def close_project_port(
    name: str,
    port_id: str,
    user: User = Depends(get_user),
    project_port_close_usecase: ProjectPortCloseUseCase = Depends(ProjectPortCloseUseCase)
):
    closed = await project_port_close_usecase(
        project_id=name,
        service_id=port_id,
    )
    return SuccessResponse(
        message="Port closed successfully",
        data=ProjectPortCloseResponse(service_closed=closed)
    )


@project_router.post("/{name}/dns", response_model=SuccessResponse[ProjectDnsCreateResponse])
async def create_project_dns(
    name: str,
    payload: ProjectDnsCreateRequest,
    user: User = Depends(get_user),
    project_dns_create_usecase: ProjectDnsCreateUseCase = Depends(ProjectDnsCreateUseCase)
):
    dns_record = await project_dns_create_usecase(
        project_id=name,
        payload=payload
    )

    return SuccessResponse(
        message="DNS record created successfully",
        data=ProjectDnsCreateResponse(
            name=dns_record.name,
            type=dns_record.type,
            value=dns_record.value
        )
    )


@project_router.delete("/{name}/dns-records/{dns_id}", response_model=SuccessResponse[ProjectDnsDeleteResponse])
async def delete_project_dns(
    name: str,
    dns_id: str, # dns_id는 subdomain으로 사용
    user: User = Depends(get_user),
    project_dns_delete_usecase: ProjectDnsDeleteUseCase = Depends(ProjectDnsDeleteUseCase)
):
    deleted = await project_dns_delete_usecase(
        project_id=name,
        subdomain=dns_id
    )

    return SuccessResponse(
        message="DNS record deleted successfully",
        data=ProjectDnsDeleteResponse(deleted=deleted)
    )


@project_router.patch("/{name}/dns-records/{dns_id}", response_model=SuccessResponse[ProjectDnsUpdateResponse])
async def update_project_dns(
    name: str,
    dns_id: str, # dns_id는 old_subdomain으로 사용
    payload: ProjectDnsUpdateRequest,
    user: User = Depends(get_user),
    project_dns_update_usecase: ProjectDnsUpdateUseCase = Depends(ProjectDnsUpdateUseCase)
):
    dns_record = await project_dns_update_usecase(
        project_id=name,
        old_subdomain=dns_id,
        payload=payload
    )

    return SuccessResponse(
        message="DNS record updated successfully",
        data=ProjectDnsUpdateResponse(
            name=dns_record.name,
            type=dns_record.type,
            value=dns_record.value
        )
    )


@project_router.patch("/{name}/dns-records/{dns_id}/port", response_model=SuccessResponse[ProjectDnsPortBindResponse])
async def bind_project_dns_port(
    name: str,
    dns_id: str, # dns_id는 subdomain으로 사용
    payload: ProjectDnsPortBindRequest,
    user: User = Depends(get_user),
    project_dns_port_bind_usecase: ProjectDnsPortBindUseCase = Depends(ProjectDnsPortBindUseCase)
):
    updated_service = await project_dns_port_bind_usecase(
        project_id=name,
        subdomain=dns_id,
        payload=payload
    )

    ports_response = [
        ServicePortResponse(
            port=p.port,
            target_port=p.target_port,
            protocol=p.protocol,
            name=p.name,
            node_port=p.node_port
        ) for p in updated_service.ports
    ]

    response = ProjectDnsPortBindResponse(
        name=updated_service.name,
        namespace=updated_service.namespace,
        ports=ports_response,
        selector=updated_service.selector,
        service_type=updated_service.service_type,
        cluster_ip=updated_service.cluster_ip,
        external_ips=updated_service.external_ips
    )
    
    return SuccessResponse(
        message="DNS record bound to service successfully",
        data=response
    )

@project_router.patch("/{name}/resource", response_model=SuccessResponse[ProjectResourceUpdateResponse])
async def update_project_resources(
    name: str,
    payload: ProjectResourceUpdateRequest,
    user: User = Depends(get_user),
    project_resource_update_usecase: ProjectResourceUpdateUseCase = Depends(ProjectResourceUpdateUseCase)
):
    updated_quota = await project_resource_update_usecase(
        project_id=name,
        payload=payload
    )

    return SuccessResponse(
        message="Project resources updated successfully",
        data=ProjectResourceUpdateResponse(
            resource_quota=updated_quota.hard_limits
        )
    )



