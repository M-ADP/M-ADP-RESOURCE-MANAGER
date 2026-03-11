from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.project.schmas.response import ProjectDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.app.project.exceptions import ProjectNotFoundException
from src.core.project import ProjectRepository
from src.dependencies.kubernetes import get_project_repository


class ProjectDeleteUseCase(BaseUseCase):

    def __init__(
            self,
            project_repo: ProjectRepository = Depends(get_project_repository),
    ):
        self.project_repo = project_repo

    async def __call__(
            self,
            id: str,
            user_id: str
    ) -> ProjectDeleteResponse:
        """Project 삭제 (ResourceQuota + Namespace)"""
        project_id = id
        namespace_id = ProjectId(project_id).namespace

        # 1. Project 존재 여부 확인
        if not await self.project_repo.exists_namespace(namespace_id):
            raise ProjectNotFoundException()

        quota_id = f"{namespace_id}-quota"

        # 2. ResourceQuota 삭제 (존재하는 경우)
        resource_quota_deleted = False
        if await self.project_repo.exists_resource_quota(quota_id, namespace_id):
            await self.project_repo.delete_resource_quota(quota_id, namespace_id)
            resource_quota_deleted = True

        # 3. Namespace 삭제
        await self.project_repo.delete_namespace(namespace_id)

        return ProjectDeleteResponse(
            namespace_id=namespace_id,
            resource_quota_deleted=resource_quota_deleted,
        )
