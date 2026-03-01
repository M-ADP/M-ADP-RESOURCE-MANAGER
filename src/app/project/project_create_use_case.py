from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectCreateRequest
from src.api.v1.project.schmas.response import ProjectCreateResponse
from src.app.base_use_case import BaseUseCase
from src.common.const import DefaultLabel
from src.core.project import ProjectRepository
from src.core.kubernetes.namespace import Namespace
from src.core.kubernetes.resource_quota import ResourceQuota, ResourceQuotaLimits
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
        """Project 생성 (Namespace + ResourceQuota)"""

        # Namespace 생성
        namespace = (
            Namespace
            .for_project(user_id=user_id, project_id=payload.id, project_name=payload.name)
            .with_labels(DefaultLabel.MANAGED_BY_LABEL)
        )
        saved_namespace = await self.project_repo.save_namespace(namespace)

        # ResourceQuota 생성
        limits = ResourceQuotaLimits(
            cpu=payload.cpu,
            memory=payload.memory,
            disk=payload.disk,
        )
        resource_quota = ResourceQuota.for_project(
            user_id=user_id,
            project_name=payload.name,
            namespace=saved_namespace.id,
            limits=limits,
        )
        saved_quota = await self.project_repo.save_resource_quota(resource_quota)

        return ProjectCreateResponse(
            namespace_id=saved_namespace.id,
            name=saved_namespace.name,
            resource_quota_id=saved_quota.id,
            limits=saved_quota.hard_limits,
        )
