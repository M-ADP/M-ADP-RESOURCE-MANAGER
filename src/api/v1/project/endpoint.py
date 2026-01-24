"""Project API 라우터"""

from fastapi import APIRouter, Depends

from src.api.v1.project.schmas.request import (
    ProjectCreateRequest,
)
from src.api.v1.project.schmas.response import ProjectCreateResponse, ProjectDeleteResponse
from src.api.v1.schema.request.user import User
from src.app.project.project_create_use_case import ProjectCreateUseCase
from src.app.project.project_delete_use_case import ProjectDeleteUseCase
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

#
# @project_router.post("/{name}/ports")
# async def open_ports

