"""Project API 라우터"""

from fastapi import APIRouter, Depends

from api.schmas.project import (
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectDeleteResponse,
)
from app.project.service import ProjectService
from core.response import SuccessResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=SuccessResponse[ProjectCreateResponse])
async def create_project(
    payload: ProjectCreateRequest,
    service : ProjectService = Depends(ProjectService)
):
    project_create_result = await service.create_project(payload)
    return SuccessResponse(
        message="Project created",
        data=project_create_result
    )


@router.delete("/{name}", response_model=SuccessResponse[ProjectDeleteResponse])
async def delete_project(
    name: str,
    service : ProjectService = Depends(ProjectService)
):
    project_delete_result = await service.delete_project(name)
    return SuccessResponse(
        message="Project deleted",
        data=project_delete_result,
    )
