from typing import List, Optional

from kubernetes_asyncio.client import V1Secret

from src.core.kubernetes.secret import Secret, SecretRepository
from src.infra.kubernetes.managers.secret import SecretManager


class K8sSecretRepository(SecretRepository):
    """Kubernetes Secret Repository 구현체"""

    def __init__(self, manager: SecretManager):
        self._manager = manager

    async def save(self, secret: Secret) -> Secret:
        v1_secret = await self._manager.create_secret(
            name=secret.name,
            namespace=secret.namespace,
            secret_type=secret.secret_type,
            data=secret.data if secret.data else None,
            string_data=secret.string_data if secret.string_data else None,
            labels=secret.labels if secret.labels else None,
            annotations=secret.annotations if secret.annotations else None,
        )
        return self._to_domain(v1_secret)

    async def find_by_name(self, name: str, namespace: str) -> Optional[Secret]:
        v1_secret = await self._manager.get_secret(name, namespace)
        if v1_secret is None:
            return None
        return self._to_domain(v1_secret)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Secret]:
        v1_secrets = await self._manager.list_secrets(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(s) for s in v1_secrets]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_secret(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_secret: V1Secret) -> Secret:
        # data는 base64로 인코딩되어 있음
        data = {}
        if v1_secret.data:
            data = {k: v for k, v in v1_secret.data.items()}

        return Secret(
            name=v1_secret.metadata.name,
            namespace=v1_secret.metadata.namespace,
            secret_type=v1_secret.type or "Opaque",
            data=data,
            labels=v1_secret.metadata.labels or {},
            annotations=v1_secret.metadata.annotations or {},
        )
