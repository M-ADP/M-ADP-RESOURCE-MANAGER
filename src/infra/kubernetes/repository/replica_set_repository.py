from typing import List, Optional

from kubernetes_asyncio.client import V1ReplicaSet

from src.core.kubernetes.replica_set import ReplicaSet, ReplicaSetStatus, ReplicaSetRepository
from src.core.kubernetes.deployment import Container
from src.infra.kubernetes.managers.replicaset import ReplicaSetManager


class K8sReplicaSetRepository(ReplicaSetRepository):
    """Kubernetes ReplicaSet Repository 구현체"""

    def __init__(self, manager: ReplicaSetManager):
        self._manager = manager

    async def save(self, replicaset: ReplicaSet) -> ReplicaSet:
        v1_rs = await self._manager.create_replicaset(
            name=replicaset.name,
            namespace=replicaset.namespace,
            replicas=replicaset.replicas,
            labels=replicaset.labels if replicaset.labels else None,
            annotations=replicaset.annotations if replicaset.annotations else None,
        )
        return self._to_domain(v1_rs)

    async def find_by_name(self, name: str, namespace: str) -> Optional[ReplicaSet]:
        v1_rs = await self._manager.get_replicaset(name, namespace)
        if v1_rs is None:
            return None
        return self._to_domain(v1_rs)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[ReplicaSet]:
        v1_rss = await self._manager.list_replicasets(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(rs) for rs in v1_rss]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_replicaset(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_rs: V1ReplicaSet) -> ReplicaSet:
        containers = []
        if v1_rs.spec and v1_rs.spec.template and v1_rs.spec.template.spec:
            for c in v1_rs.spec.template.spec.containers or []:
                containers.append(Container(
                    name=c.name,
                    image=c.image,
                ))

        status = None
        if v1_rs.status:
            status = ReplicaSetStatus(
                replicas=v1_rs.status.replicas,
                ready_replicas=v1_rs.status.ready_replicas,
                available_replicas=v1_rs.status.available_replicas,
            )

        return ReplicaSet(
            name=v1_rs.metadata.name,
            namespace=v1_rs.metadata.namespace,
            replicas=v1_rs.spec.replicas if v1_rs.spec else 1,
            containers=containers,
            labels=v1_rs.metadata.labels or {},
            annotations=v1_rs.metadata.annotations or {},
            selector_labels=v1_rs.spec.selector.match_labels if v1_rs.spec and v1_rs.spec.selector else {},
            status=status,
        )
