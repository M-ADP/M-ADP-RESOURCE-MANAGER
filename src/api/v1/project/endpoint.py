"""Project API 라우터"""

from fastapi import APIRouter, Depends

from src.api.v1.deps.user import get_user
from src.api.v1.project.schmas.request import ProjectCreateRequest, ProjectResourceUpdateRequest
from src.api.v1.project.schmas.response import (
    ProjectCreateResponse, ProjectDeleteResponse, ProjectResourceUpdateResponse,
)
from src.app.project.project_create_use_case import ProjectCreateUseCase
from src.app.project.project_delete_use_case import ProjectDeleteUseCase
from src.app.project.project_resource_update_use_case import ProjectResourceUpdateUseCase
from src.app.monitoring.project_resource_status_use_case import ProjectResourceStatusUseCase
from src.app.monitoring.dto import ProjectResourceStatusResponse
from src.core.response import SuccessResponse
from src.core.user.model import User

project_router = APIRouter(prefix="/projects", tags=["projects"])


@project_router.get("/{name}/resource", response_model=SuccessResponse[ProjectResourceStatusResponse])
async def get_project_resources(
    name: str,
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
    project_create_usecase: ProjectCreateUseCase = Depends(ProjectCreateUseCase)
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
    project_delete_usecase: ProjectDeleteUseCase = Depends(ProjectDeleteUseCase)
):
    project_delete_result = await project_delete_usecase(
        name,
        user.id
    )
    return SuccessResponse(
        message="Project deleted",
        data=project_delete_result,
    )


@project_router.patch("/{name}/resource", response_model=SuccessResponse[ProjectResourceUpdateResponse])
async def update_project_resources(
    name: str,
    payload: ProjectResourceUpdateRequest,
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
