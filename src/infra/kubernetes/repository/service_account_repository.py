from typing import List, Optional

from kubernetes_asyncio.client import V1ServiceAccount

from src.core.kubernetes.service_account import ServiceAccount, ServiceAccountRepository
from src.infra.kubernetes.managers.serviceaccount import ServiceAccountManager


class K8sServiceAccountRepository(ServiceAccountRepository):
    """Kubernetes ServiceAccount Repository 구현체"""

    def __init__(self, manager: ServiceAccountManager):
        self._manager = manager

    async def save(self, service_account: ServiceAccount) -> ServiceAccount:
        v1_sa = await self._manager.create_service_account(
            name=service_account.name,
            namespace=service_account.namespace,
            labels=service_account.labels if service_account.labels else None,
            annotations=service_account.annotations if service_account.annotations else None,
            image_pull_secrets=service_account.image_pull_secrets if service_account.image_pull_secrets else None,
        )
        return self._to_domain(v1_sa)

    async def find_by_name(self, name: str, namespace: str) -> Optional[ServiceAccount]:
        v1_sa = await self._manager.get_service_account(name, namespace)
        if v1_sa is None:
            return None
        return self._to_domain(v1_sa)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[ServiceAccount]:
        v1_sas = await self._manager.list_service_accounts(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(sa) for sa in v1_sas]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_service_account(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_sa: V1ServiceAccount) -> ServiceAccount:
        image_pull_secrets = []
        if v1_sa.image_pull_secrets:
            image_pull_secrets = [s.name for s in v1_sa.image_pull_secrets]

        return ServiceAccount(
            name=v1_sa.metadata.name,
            namespace=v1_sa.metadata.namespace,
            labels=v1_sa.metadata.labels or {},
            annotations=v1_sa.metadata.annotations or {},
            image_pull_secrets=image_pull_secrets,
        )
