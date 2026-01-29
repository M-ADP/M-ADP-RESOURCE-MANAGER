from typing import List, Optional

from kubernetes_asyncio.client import V1StatefulSet

from src.core.kubernetes.statefulset import StatefulSet, StatefulSetStatus, StatefulSetRepository
from src.core.kubernetes.deployment import Container
from src.infra.kubernetes.managers.statefulset import StatefulSetManager


class K8sStatefulSetRepository(StatefulSetRepository):
    """Kubernetes StatefulSet Repository 구현체"""

    def __init__(self, manager: StatefulSetManager):
        self._manager = manager

    async def save(self, statefulset: StatefulSet) -> StatefulSet:
        v1_sts = await self._manager.create_statefulset(
            name=statefulset.name,
            namespace=statefulset.namespace,
            service_name=statefulset.service_name,
            replicas=statefulset.replicas,
            labels=statefulset.labels if statefulset.labels else None,
            annotations=statefulset.annotations if statefulset.annotations else None,
        )
        return self._to_domain(v1_sts)

    async def find_by_name(self, name: str, namespace: str) -> Optional[StatefulSet]:
        v1_sts = await self._manager.get_statefulset(name, namespace)
        if v1_sts is None:
            return None
        return self._to_domain(v1_sts)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[StatefulSet]:
        v1_stss = await self._manager.list_statefulsets(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(sts) for sts in v1_stss]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_statefulset(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_sts: V1StatefulSet) -> StatefulSet:
        containers = []
        if v1_sts.spec and v1_sts.spec.template and v1_sts.spec.template.spec:
            for c in v1_sts.spec.template.spec.containers or []:
                containers.append(Container(
                    name=c.name,
                    image=c.image,
                ))

        status = None
        if v1_sts.status:
            status = StatefulSetStatus(
                replicas=v1_sts.status.replicas,
                ready_replicas=v1_sts.status.ready_replicas,
                current_replicas=v1_sts.status.current_replicas,
                updated_replicas=v1_sts.status.updated_replicas,
            )

        return StatefulSet(
            name=v1_sts.metadata.name,
            namespace=v1_sts.metadata.namespace,
            service_name=v1_sts.spec.service_name if v1_sts.spec else "",
            replicas=v1_sts.spec.replicas if v1_sts.spec else 1,
            containers=containers,
            labels=v1_sts.metadata.labels or {},
            annotations=v1_sts.metadata.annotations or {},
            selector_labels=v1_sts.spec.selector.match_labels if v1_sts.spec and v1_sts.spec.selector else {},
            status=status,
        )
