from typing import List, Optional

from kubernetes_asyncio.client import V1PersistentVolumeClaim

from src.core.kubernetes.persistent_volume_claim import PersistentVolumeClaim, PersistentVolumeClaimRepository
from src.infra.kubernetes.managers.persistentvolumeclaim import PersistentVolumeClaimManager


class K8sPersistentVolumeClaimRepository(PersistentVolumeClaimRepository):
    """Kubernetes PersistentVolumeClaim Repository 구현체"""

    def __init__(self, manager: PersistentVolumeClaimManager):
        self._manager = manager

    async def save(self, pvc: PersistentVolumeClaim) -> PersistentVolumeClaim:
        v1_pvc = await self._manager.create_persistent_volume_claim(
            name=pvc.name,
            namespace=pvc.namespace,
            storage_class_name=pvc.storage_class_name,
            access_modes=pvc.access_modes,
            storage=pvc.storage,
            labels=pvc.labels if pvc.labels else None,
            annotations=pvc.annotations if pvc.annotations else None,
        )
        return self._to_domain(v1_pvc)

    async def find_by_name(self, name: str, namespace: str) -> Optional[PersistentVolumeClaim]:
        v1_pvc = await self._manager.get_persistent_volume_claim(name, namespace)
        if v1_pvc is None:
            return None
        return self._to_domain(v1_pvc)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[PersistentVolumeClaim]:
        v1_pvcs = await self._manager.list_persistent_volume_claims(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(pvc) for pvc in v1_pvcs]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_persistent_volume_claim(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_pvc: V1PersistentVolumeClaim) -> PersistentVolumeClaim:
        storage = "1Gi"
        if v1_pvc.spec and v1_pvc.spec.resources and v1_pvc.spec.resources.requests:
            storage = v1_pvc.spec.resources.requests.get("storage", "1Gi")

        return PersistentVolumeClaim(
            name=v1_pvc.metadata.name,
            namespace=v1_pvc.metadata.namespace,
            storage_class_name=v1_pvc.spec.storage_class_name if v1_pvc.spec else None,
            access_modes=v1_pvc.spec.access_modes if v1_pvc.spec else ["ReadWriteOnce"],
            storage=storage,
            labels=v1_pvc.metadata.labels or {},
            annotations=v1_pvc.metadata.annotations or {},
            volume_mode=v1_pvc.spec.volume_mode if v1_pvc.spec else "Filesystem",
            phase=v1_pvc.status.phase if v1_pvc.status else None,
        )
