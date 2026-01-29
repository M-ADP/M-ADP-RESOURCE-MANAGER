from fastapi import Depends

from src.api.v1.project.schmas.response import ProjectDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.dependencies.kubernetes import get_namespace_repository, get_resource_quota_repository
from src.core.kubernetes.namespace import NamespaceRepository
from src.core.kubernetes.resource_quota import ResourceQuotaRepository


class ProjectDeleteUseCase(BaseUseCase):

    def __init__(
            self,
            namespace_repo: NamespaceRepository = Depends(get_namespace_repository),
            resource_quota_repo: ResourceQuotaRepository = Depends(get_resource_quota_repository),
    ):
        self.namespace_repo = namespace_repo
        self.resource_quota_repo = resource_quota_repo

    async def __call__(
            self,
            id: str,
            user_id: str
    ) -> ProjectDeleteResponse:
        """Project 삭제 (ResourceQuota + Namespace)"""
        project_id = id
        quota_id = f"{id}-quota"

        # ResourceQuota 삭제 (존재하는 경우)
        resource_quota_deleted = False
        if await self.resource_quota_repo.exists(quota_id, project_id):
            await self.resource_quota_repo.delete(quota_id, project_id)
            resource_quota_deleted = True

        # Namespace 삭제
        await self.namespace_repo.delete(project_id)

        return ProjectDeleteResponse(
            namespace_id=project_id,
            resource_quota_deleted=resource_quota_deleted,
        )
