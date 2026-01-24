from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectCreateRequest
from src.api.v1.project.schmas.response import ProjectCreateResponse
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_kubernetes_client
from src.infra.kubernetes import NamespaceManager, KubernetesClientImpl
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.resourcequota.model import ResourceQuotaLimits


class ProjectCreateUseCase(BaseUseCase):

    def __init__(
            self,
            k8s_client : KubernetesClientImpl = Depends(get_kubernetes_client),
    ):
        self.namespace_manager = NamespaceManager(k8s_client)
        self.resource_quota_manager = ResourceQuotaManager(k8s_client)


    async def __call__(
            self,
            payload: ProjectCreateRequest,
    ) -> ProjectCreateResponse:
        """Project 생성 (Namespace + ResourceQuota)"""
        namespace_name = payload.name
        await self.namespace_manager.create_namespace(name=namespace_name)

        quota_name = f"{namespace_name}-quota"
        resource_limits = ResourceQuotaLimits(
            cpu=payload.cpu,
            memory=payload.memory,
            disk=payload.disk,
        )
        await self.resource_quota_manager.create_resource_quota(
            name=quota_name,
            namespace=namespace_name,
            hard_limits=resource_limits.to_dict(),
        )

        return ProjectCreateResponse(
            namespace=namespace_name,
            resource_quota=quota_name,
            limits=resource_limits.to_dict(),
        )