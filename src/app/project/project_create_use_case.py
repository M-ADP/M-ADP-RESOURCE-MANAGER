from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectCreateRequest
from src.api.v1.project.schmas.response import ProjectCreateResponse
from src.app.base_use_case import BaseUseCase
from src.core.project import ProjectRepository
from src.core.project.model import Project
from src.dependencies.kubernetes import get_project_repository


class ProjectCreateUseCase(BaseUseCase):

    def __init__(
            self,
            project_repo: ProjectRepository = Depends(get_project_repository),
    ):
        self.project_repo = project_repo

    async def __call__(
            self,
            payload: ProjectCreateRequest,
            user_id: str
    ) -> ProjectCreateResponse:
        """Project 생성 (Namespace + ResourceQuota + Harbor imagePullSecret + SA)"""

        project = Project(
            id=payload.id,
            name=payload.name,
            user_id=user_id,
            cpu=payload.cpu,
            memory=payload.memory,
            disk=payload.disk,
        )
        result = await self.project_repo.save(project)

        return ProjectCreateResponse(
            namespace_id=result.namespace,
            name=result.name,
            resource_quota_id=result.resource_quota_id,
            limits=result.limits,
        )
