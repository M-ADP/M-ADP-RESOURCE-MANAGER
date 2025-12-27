"""Project API 라우터"""

from fastapi import APIRouter, Depends

from api.schmas.project import ProjectCreateRequest, ProjectCreateResponse
from app.project.service import create_project as create_project_service
from core.response import SuccessResponse
from infra.kubernetes.client import KubernetesClient, get_kubernetes_client

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=SuccessResponse[ProjectCreateResponse])
async def create_project(
    payload: ProjectCreateRequest,
    k8s_client: KubernetesClient = Depends(get_kubernetes_client),
):
    project_create_result = await create_project_service(payload, k8s_client)
    return SuccessResponse(
        message="Project created",
        data=project_create_result,
    )
