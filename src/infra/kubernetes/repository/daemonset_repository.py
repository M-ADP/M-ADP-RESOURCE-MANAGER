from typing import List, Optional

from kubernetes_asyncio.client import V1DaemonSet

from src.core.kubernetes.daemonset import DaemonSet, DaemonSetStatus, DaemonSetRepository
from src.core.kubernetes.deployment.model import Container
from src.infra.kubernetes.managers.daemonset import DaemonSetManager


class K8sDaemonSetRepository(DaemonSetRepository):
    """Kubernetes DaemonSet Repository 구현체"""

    def __init__(self, manager: DaemonSetManager):
        self._manager = manager

    async def save(self, daemonset: DaemonSet) -> DaemonSet:
        v1_ds = await self._manager.create_daemonset(
            name=daemonset.name,
            namespace=daemonset.namespace,
            labels=daemonset.labels if daemonset.labels else None,
            annotations=daemonset.annotations if daemonset.annotations else None,
        )
        return self._to_domain(v1_ds)

    async def find_by_name(self, name: str, namespace: str) -> Optional[DaemonSet]:
        v1_ds = await self._manager.get_daemonset(name, namespace)
        if v1_ds is None:
            return None
        return self._to_domain(v1_ds)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[DaemonSet]:
        v1_dss = await self._manager.list_daemonsets(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(ds) for ds in v1_dss]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_daemonset(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_ds: V1DaemonSet) -> DaemonSet:
        containers = []
        if v1_ds.spec and v1_ds.spec.template and v1_ds.spec.template.spec:
            for c in v1_ds.spec.template.spec.containers or []:
                containers.append(Container(
                    name=c.name,
                    image=c.image,
                ))

        status = None
        if v1_ds.status:
            status = DaemonSetStatus(
                current_number_scheduled=v1_ds.status.current_number_scheduled,
                desired_number_scheduled=v1_ds.status.desired_number_scheduled,
                number_available=v1_ds.status.number_available,
                number_ready=v1_ds.status.number_ready,
            )

        return DaemonSet(
            name=v1_ds.metadata.name,
            namespace=v1_ds.metadata.namespace,
            containers=containers,
            labels=v1_ds.metadata.labels or {},
            annotations=v1_ds.metadata.annotations or {},
            selector_labels=v1_ds.spec.selector.match_labels if v1_ds.spec and v1_ds.spec.selector else {},
            status=status,
        )
