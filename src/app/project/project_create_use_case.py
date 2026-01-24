from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectCreateRequest
from src.api.v1.project.schmas.response import ProjectCreateResponse
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_kubernetes_client, get_namespace_repository
from src.core.kubernetes.namespace import Namespace, NamespaceRepository
from src.infra.kubernetes import KubernetesClientImpl
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.resourcequota.model import ResourceQuotaLimits


class ProjectCreateUseCase(BaseUseCase):

    def __init__(
            self,
            namespace_repo: NamespaceRepository = Depends(get_namespace_repository),
            k8s_client: KubernetesClientImpl = Depends(get_kubernetes_client),
    ):
        self.namespace_repo = namespace_repo
        # TODO: ResourceQuotaRepository로 전환 예정
        self.resource_quota_manager = ResourceQuotaManager(k8s_client)

    async def __call__(
            self,
            payload: ProjectCreateRequest,
            user_id: str
    ) -> ProjectCreateResponse:
        """Project 생성 (Namespace + ResourceQuota)"""
        # 도메인 객체 생성
        namespace = Namespace(name=payload.name)

        # Repository를 통해 저장
        saved_namespace = await self.namespace_repo.save(namespace)

        quota_name = f"{user_id}-{saved_namespace.name}-quota"
        resource_limits = ResourceQuotaLimits(
            cpu=payload.cpu,
            memory=payload.memory,
            disk=payload.disk,
        )
        await self.resource_quota_manager.create_resource_quota(
            name=quota_name,
            namespace=saved_namespace.name,
            hard_limits=resource_limits.to_dict(),
        )

        return ProjectCreateResponse(
            namespace=saved_namespace.name,
            resource_quota=quota_name,
            limits=resource_limits.to_dict(),
        )
