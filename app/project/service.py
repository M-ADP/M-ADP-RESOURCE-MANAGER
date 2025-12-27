"""Project 비즈니스 로직"""

from api.schmas.project import ProjectCreateRequest, ProjectCreateResponse
from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.namespace import NamespaceManager
from infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from infra.kubernetes.managers.resourcequota.model import ResourceQuotaLimits


async def create_project(
    payload: ProjectCreateRequest,
    k8s_client: KubernetesClient,
) -> ProjectCreateResponse:
    """Project 생성 (Namespace + ResourceQuota)"""
    namespace_manager = NamespaceManager(k8s_client)
    resource_quota_manager = ResourceQuotaManager(k8s_client)

    namespace_name = payload.name
    await namespace_manager.create_namespace(name=namespace_name)

    quota_name = f"{namespace_name}-quota"
    resource_limits = ResourceQuotaLimits(
        cpu=payload.cpu,
        memory=payload.memory,
        disk=payload.disk,
    )
    await resource_quota_manager.create_resource_quota(
        name=quota_name,
        namespace=namespace_name,
        hard_limits=resource_limits.to_dict(),
    )

    return ProjectCreateResponse(
        namespace=namespace_name,
        resource_quota=quota_name,
        limits=resource_limits.to_dict(),
    )
