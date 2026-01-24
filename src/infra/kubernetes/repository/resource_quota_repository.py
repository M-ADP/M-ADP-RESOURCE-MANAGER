from typing import List, Optional

from kubernetes_asyncio.client import V1ResourceQuota

from src.core.kubernetes.resource_quota import ResourceQuota, ResourceQuotaRepository
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager


class K8sResourceQuotaRepository(ResourceQuotaRepository):
    """Kubernetes ResourceQuota Repository 구현체"""

    def __init__(self, manager: ResourceQuotaManager):
        self._manager = manager

    async def save(self, resource_quota: ResourceQuota) -> ResourceQuota:
        """ResourceQuota 저장 (생성 또는 업데이트, 멱등성 보장)"""
        v1_rq = await self._manager.create_resource_quota(
            name=resource_quota.name,
            namespace=resource_quota.namespace,
            hard_limits=resource_quota.hard_limits,
            labels=resource_quota.labels if resource_quota.labels else None,
            annotations=resource_quota.annotations if resource_quota.annotations else None,
        )
        return self._to_domain(v1_rq)

    async def find_by_name(self, name: str, namespace: str) -> Optional[ResourceQuota]:
        """이름과 네임스페이스로 ResourceQuota 조회"""
        v1_rq = await self._manager.get_resource_quota(name, namespace)
        if v1_rq is None:
            return None
        return self._to_domain(v1_rq)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[ResourceQuota]:
        """ResourceQuota 목록 조회"""
        v1_rqs = await self._manager.list_resource_quotas(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(rq) for rq in v1_rqs]

    async def delete(self, name: str, namespace: str) -> bool:
        """ResourceQuota 삭제"""
        return await self._manager.delete_resource_quota(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        """ResourceQuota 존재 여부 확인"""
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_rq: V1ResourceQuota) -> ResourceQuota:
        """V1ResourceQuota를 도메인 객체로 변환"""
        return ResourceQuota(
            name=v1_rq.metadata.name,
            namespace=v1_rq.metadata.namespace,
            hard_limits=v1_rq.spec.hard if v1_rq.spec and v1_rq.spec.hard else {},
            used=v1_rq.status.used if v1_rq.status and v1_rq.status.used else {},
            labels=v1_rq.metadata.labels or {},
            annotations=v1_rq.metadata.annotations or {},
        )
