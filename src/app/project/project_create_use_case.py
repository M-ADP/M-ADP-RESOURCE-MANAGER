from fastapi import Depends

from src.app.base_use_case import BaseUseCase
from src.infra.kubernetes import KubernetesClientImpl, NamespaceManager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager


class ProjectCreateUseCase(BaseUseCase):

    def __init__(
            self,
            k8s_client : KubernetesClientImpl = Depends(get_kubernetes_client),
    ):
        self.namespace_manager = NamespaceManager(k8s_client)
        self.resource_quota_manager = ResourceQuotaManager(k8s_client)


    async def __call__(self):
        pass