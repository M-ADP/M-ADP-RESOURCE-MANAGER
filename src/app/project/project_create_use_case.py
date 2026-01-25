from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectCreateRequest
from src.api.v1.project.schmas.response import ProjectCreateResponse
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_namespace_repository, get_resource_quota_repository
from src.core.kubernetes.namespace import Namespace, NamespaceRepository
from src.core.kubernetes.resource_quota import ResourceQuota, ResourceQuotaLimits, ResourceQuotaRepository

# MANAGED_BY_LABEL = {"managed-by": "madp"}


class ProjectCreateUseCase(BaseUseCase):

    def __init__(
            self,
            namespace_repo: NamespaceRepository = Depends(get_namespace_repository),
            resource_quota_repo: ResourceQuotaRepository = Depends(get_resource_quota_repository),
    ):
        self.namespace_repo = namespace_repo
        self.resource_quota_repo = resource_quota_repo

    async def __call__(
            self,
            payload: ProjectCreateRequest,
            user_id: str
    ) -> ProjectCreateResponse:
        """Project 생성 (Namespace + ResourceQuota)"""
        # Namespace 도메인 객체 생성 및 저장
        namespace = Namespace.for_project(user_id, payload.id, payload.name).with_labels(MANAGED_BY_LABEL)
        saved_namespace = await self.namespace_repo.save(namespace)

        # ResourceQuota 도메인 객체 생성 및 저장
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
            # labels=MANAGED_BY_LABEL,
        )
        saved_quota = await self.resource_quota_repo.save(resource_quota)

        return ProjectCreateResponse(
            namespace_id=saved_namespace.id,
            name=saved_namespace.name,
            resource_quota_id=saved_quota.id,
            limits=saved_quota.hard_limits,
        )
