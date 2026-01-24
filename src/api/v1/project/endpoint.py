"""Project API 라우터"""

from fastapi import APIRouter, Depends

from src.api.v1.project.schmas.request import (
    ProjectCreateRequest,
)
from src.api.v1.project.schmas.response import ProjectCreateResponse, ProjectDeleteResponse
from src.app.project.project_create_use_case import ProjectCreateUseCase
from src.app.project.project_delete_use_case import ProjectDeleteUseCase
from src.core.response import SuccessResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=SuccessResponse[ProjectCreateResponse])
async def create_project(
    payload: ProjectCreateRequest,
    project_create_usecase : ProjectCreateUseCase = Depends(ProjectCreateUseCase)
):
    project_create_result = await project_create_usecase(payload)
    return SuccessResponse(
        message="Project created",
        data=project_create_result
    )


@router.delete("/{name}", response_model=SuccessResponse[ProjectDeleteResponse])
async def delete_project(
    name: str,
    project_delete_usecase : ProjectDeleteUseCase = Depends(ProjectDeleteUseCase)
):
    project_delete_result = await project_delete_usecase(name)
    return SuccessResponse(
        message="Project deleted",
        data=project_delete_result,
    )
