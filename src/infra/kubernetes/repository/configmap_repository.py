from typing import List, Optional

from kubernetes_asyncio.client import V1ConfigMap

from src.core.kubernetes.configmap import ConfigMap, ConfigMapRepository
from src.infra.kubernetes.managers.configmap import ConfigMapManager


class K8sConfigMapRepository(ConfigMapRepository):
    """Kubernetes ConfigMap Repository 구현체"""

    def __init__(self, manager: ConfigMapManager):
        self._manager = manager

    async def save(self, configmap: ConfigMap) -> ConfigMap:
        v1_cm = await self._manager.create_configmap(
            name=configmap.name,
            namespace=configmap.namespace,
            data=configmap.data if configmap.data else None,
            binary_data=configmap.binary_data,
            labels=configmap.labels if configmap.labels else None,
            annotations=configmap.annotations if configmap.annotations else None,
        )
        return self._to_domain(v1_cm)

    async def find_by_name(self, name: str, namespace: str) -> Optional[ConfigMap]:
        v1_cm = await self._manager.get_configmap(name, namespace)
        if v1_cm is None:
            return None
        return self._to_domain(v1_cm)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[ConfigMap]:
        v1_cms = await self._manager.list_configmaps(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(cm) for cm in v1_cms]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_configmap(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_cm: V1ConfigMap) -> ConfigMap:
        return ConfigMap(
            name=v1_cm.metadata.name,
            namespace=v1_cm.metadata.namespace,
            data=v1_cm.data or {},
            binary_data=v1_cm.binary_data,
            labels=v1_cm.metadata.labels or {},
            annotations=v1_cm.metadata.annotations or {},
        )
