from typing import List, Optional

from kubernetes_asyncio.client import V1LimitRange

from src.core.kubernetes.limit_range import LimitRange, LimitRangeItem, LimitRangeRepository
from src.infra.kubernetes.managers.limitrange import LimitRangeManager


class K8sLimitRangeRepository(LimitRangeRepository):
    """Kubernetes LimitRange Repository 구현체"""

    def __init__(self, manager: LimitRangeManager):
        self._manager = manager

    async def save(self, limit_range: LimitRange) -> LimitRange:
        limits = [
            {
                "type": item.type,
                "default": item.default,
                "defaultRequest": item.default_request,
                "max": item.max,
                "min": item.min,
                "maxLimitRequestRatio": item.max_limit_request_ratio,
            }
            for item in limit_range.limits
        ]
        v1_lr = await self._manager.create_limit_range(
            name=limit_range.name,
            namespace=limit_range.namespace,
            limits=limits,
            labels=limit_range.labels if limit_range.labels else None,
            annotations=limit_range.annotations if limit_range.annotations else None,
        )
        return self._to_domain(v1_lr)

    async def find_by_name(self, name: str, namespace: str) -> Optional[LimitRange]:
        v1_lr = await self._manager.get_limit_range(name, namespace)
        if v1_lr is None:
            return None
        return self._to_domain(v1_lr)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[LimitRange]:
        v1_lrs = await self._manager.list_limit_ranges(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(lr) for lr in v1_lrs]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_limit_range(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_lr: V1LimitRange) -> LimitRange:
        limits = []
        if v1_lr.spec and v1_lr.spec.limits:
            for item in v1_lr.spec.limits:
                limits.append(LimitRangeItem(
                    type=item.type,
                    default=item.default,
                    default_request=item.default_request,
                    max=item.max,
                    min=item.min,
                    max_limit_request_ratio=item.max_limit_request_ratio,
                ))

        return LimitRange(
            name=v1_lr.metadata.name,
            namespace=v1_lr.metadata.namespace,
            limits=limits,
            labels=v1_lr.metadata.labels or {},
            annotations=v1_lr.metadata.annotations or {},
        )
