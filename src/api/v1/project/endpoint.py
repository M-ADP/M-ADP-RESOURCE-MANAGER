"""Project API 라우터"""

from fastapi import APIRouter, Depends

from src.api.v1.project.schmas.request import (
    ProjectCreateRequest, ProjectPortOpenRequest, ProjectPortUpdateRequest, ProjectDnsCreateRequest,
    ProjectDnsUpdateRequest,
)
from src.api.v1.project.schmas.response import (
    ProjectCreateResponse, ProjectDeleteResponse, ProjectPortOpenResponse, ServicePortResponse, ProjectPortCloseResponse,
    ProjectPortUpdateResponse, ProjectDnsCreateResponse, ProjectDnsDeleteResponse, ProjectDnsUpdateResponse,
)
from src.api.v1.schema.request.user import User
from src.app.project.project_create_use_case import ProjectCreateUseCase
from src.app.project.project_delete_use_case import ProjectDeleteUseCase
from src.app.project.project_port_open_use_case import ProjectPortOpenUseCase
from src.app.project.project_port_close_use_case import ProjectPortCloseUseCase
from src.app.project.project_port_update_use_case import ProjectPortUpdateUseCase
from src.app.project.project_dns_create_use_case import ProjectDnsCreateUseCase
from src.app.project.project_dns_delete_use_case import ProjectDnsDeleteUseCase
from src.app.project.project_dns_update_use_case import ProjectDnsUpdateUseCase
from src.core.response import SuccessResponse

project_router = APIRouter(prefix="/projects", tags=["projects"])


@project_router.post("", response_model=SuccessResponse[ProjectCreateResponse])
async def create_project(
    payload: ProjectCreateRequest,
    user : User = Depends(),
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
    user : User = Depends(),
    project_delete_usecase : ProjectCreateUseCase = Depends(ProjectCreateUseCase)
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
    user: User = Depends(),
    project_port_open_usecase: ProjectPortOpenUseCase = Depends(ProjectPortOpenUseCase)
):
    service = await project_port_open_usecase(
        project_name=name,
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
    port_id: int, # path parameter로 받은 포트 번호
    payload: ProjectPortUpdateRequest,
    user: User = Depends(),
    project_port_update_usecase: ProjectPortUpdateUseCase = Depends(ProjectPortUpdateUseCase)
):
    service = await project_port_update_usecase(
        project_name=name,
        port_number=port_id, # Path Parameter에서 받은 포트 번호를 전달
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
    port_id: str, # port_id를 service_name으로 사용
    user: User = Depends(),
    project_port_close_usecase: ProjectPortCloseUseCase = Depends(ProjectPortCloseUseCase)
):
    closed = await project_port_close_usecase(
        project_name=name,
        service_name=port_id, # service_name으로 전달
    )
    return SuccessResponse(
        message="Port closed successfully",
        data=ProjectPortCloseResponse(service_closed=closed)
    )


@project_router.post("/{name}/dns", response_model=SuccessResponse[ProjectDnsCreateResponse])
async def create_project_dns(
    name: str,
    payload: ProjectDnsCreateRequest,
    user: User = Depends(),
    project_dns_create_usecase: ProjectDnsCreateUseCase = Depends(ProjectDnsCreateUseCase)
):
    dns_record = await project_dns_create_usecase(
        project_name=name,
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
    user: User = Depends(),
    project_dns_delete_usecase: ProjectDnsDeleteUseCase = Depends(ProjectDnsDeleteUseCase)
):
    deleted = await project_dns_delete_usecase(
        project_name=name,
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
    user: User = Depends(),
    project_dns_update_usecase: ProjectDnsUpdateUseCase = Depends(ProjectDnsUpdateUseCase)
):
    dns_record = await project_dns_update_usecase(
        project_name=name,
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



