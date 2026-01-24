from fastapi import Depends

from src.api.v1.project.schmas.response import ProjectDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_kubernetes_client
from src.infra.kubernetes import NamespaceManager, KubernetesClientImpl
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager


class ProjectDeleteUseCase(BaseUseCase):

    def __init__(
            self,
            k8s_client : KubernetesClientImpl = Depends(get_kubernetes_client),
    ):
        self.namespace_manager = NamespaceManager(k8s_client)
        self.resource_quota_manager = ResourceQuotaManager(k8s_client)

    async def __call__(
            self,
            name : str,
            user_id : str
    ) -> ProjectDeleteResponse:
        """Project 삭제 (ResourceQuota + Namespace)"""
        project_name = f"{user_id}-{name}"

        quota_name = f"{name}-quota"
        existing_quota = await self.resource_quota_manager.get_resource_quota(
            name=quota_name,
            namespace=project_name,
        )
        resource_quota_deleted = False
        if existing_quota:
            await self.resource_quota_manager.delete_resource_quota(
                name=quota_name,
                namespace=project_name,
            )
            resource_quota_deleted = True

        await self.namespace_manager.delete_namespace(
            name=project_name
        )

        return ProjectDeleteResponse(
            namespace=project_name,
            resource_quota_deleted=resource_quota_deleted,
        )