"""Project 비즈니스 로직"""
from fastapi.params import Depends

from api.schmas.project import (
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectDeleteResponse,
)
from infra.kubernetes import KubernetesClient, get_kubernetes_client
from infra.kubernetes.managers.namespace import NamespaceManager
from infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from infra.kubernetes.managers.resourcequota.model import ResourceQuotaLimits

class ProjectService:

    def __init__(
            self,
            k8s_client : KubernetesClient = Depends(get_kubernetes_client),
    ):
        self.namespace_manager = NamespaceManager(k8s_client)
        self.resource_quota_manager = ResourceQuotaManager(k8s_client)

    async def create_project(
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


    async def delete_project(
        self,
        name: str
    ) -> ProjectDeleteResponse:
        """Project 삭제 (ResourceQuota + Namespace)"""
        quota_name = f"{name}-quota"
        existing_quota = await self.resource_quota_manager.get_resource_quota(
            name=quota_name,
            namespace=name,
        )
        resource_quota_deleted = False
        if existing_quota:
            await self.resource_quota_manager.delete_resource_quota(
                name=quota_name,
                namespace=name,
            )
            resource_quota_deleted = True

        await self.namespace_manager.delete_namespace(name=name)

        return ProjectDeleteResponse(
            namespace=name,
            resource_quota_deleted=resource_quota_deleted,
        )

