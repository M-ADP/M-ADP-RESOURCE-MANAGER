"""Project API 라우터"""

from fastapi import APIRouter, Depends

from src.api.v1.project.schmas.request import (
    ProjectCreateRequest, ProjectPortOpenRequest,
)
from src.api.v1.project.schmas.response import (
    ProjectCreateResponse, ProjectDeleteResponse, ProjectPortOpenResponse, ProjectPortDeleteResponse,
)
from src.api.v1.schema.request.user import User
from src.app.project.project_create_use_case import ProjectCreateUseCase
from src.app.project.project_delete_use_case import ProjectDeleteUseCase
from src.app.project.project_port_open_use_case import ProjectPortOpenUseCase
from src.app.project.project_port_delete_use_case import ProjectPortDeleteUseCase
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
    user: User = Depends(),
    project_port_open_usecase: ProjectPortOpenUseCase = Depends(ProjectPortOpenUseCase)
):
    gateway = await project_port_open_usecase(
        project_name=name,
        payload=payload
    )
    
    server = gateway.servers[0]
    response = ProjectPortOpenResponse(
        gateway_name=gateway.name,
        namespace=gateway.namespace,
        port=server.port.number,
        protocol=server.port.protocol,
        hosts=server.hosts
    )

    return SuccessResponse(
        message="Port opened successfully",
        data=response
    )


@project_router.delete("/{name}/ports/{port_id}", response_model=SuccessResponse[ProjectPortDeleteResponse])
async def delete_project_port(
    name: str,
    port_id: int,
    user: User = Depends(),
    project_port_delete_usecase: ProjectPortDeleteUseCase = Depends(ProjectPortDeleteUseCase)
):
    deleted = await project_port_delete_usecase(
        project_name=name,
        port_id=port_id,
    )
    return SuccessResponse(
        message="Port deleted successfully",
        data=ProjectPortDeleteResponse(gateway_deleted=deleted)
    )
