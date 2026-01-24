from typing import List, Optional

from kubernetes_asyncio.client import V1Namespace

from src.core.kubernetes.namespace import Namespace, NamespaceRepository
from src.infra.kubernetes.managers.namespace import NamespaceManager


class K8sNamespaceRepository(NamespaceRepository):
    """Kubernetes Namespace Repository 구현체"""
    
    def __init__(self, manager: NamespaceManager):
        self._manager = manager
    
    async def save(self, namespace: Namespace) -> Namespace:
        """Namespace 저장 (생성 또는 업데이트, 멱등성 보장)"""
        v1_namespace = await self._manager.create_namespace(
            name=namespace.name,
            labels=namespace.labels if namespace.labels else None,
            annotations=namespace.annotations if namespace.annotations else None,
        )
        return self._to_domain(v1_namespace)
    
    async def find_by_name(self, name: str) -> Optional[Namespace]:
        """이름으로 Namespace 조회"""
        v1_namespace = await self._manager.get_namespace(name)
        if v1_namespace is None:
            return None
        return self._to_domain(v1_namespace)
    
    async def find_all(
        self,
        label_selector: Optional[str] = None,
    ) -> List[Namespace]:
        """Namespace 목록 조회"""
        v1_namespaces = await self._manager.list_namespaces(
            label_selector=label_selector,
        )
        return [self._to_domain(ns) for ns in v1_namespaces]
    
    async def delete(self, name: str) -> bool:
        """Namespace 삭제"""
        return await self._manager.delete_namespace(name)
    
    async def exists(self, name: str) -> bool:
        """Namespace 존재 여부 확인"""
        return await self._manager.exists(name)
    
    def _to_domain(self, v1_namespace: V1Namespace) -> Namespace:
        """V1Namespace를 도메인 객체로 변환"""
        return Namespace(
            name=v1_namespace.metadata.name,
            labels=v1_namespace.metadata.labels or {},
            annotations=v1_namespace.metadata.annotations or {},
            status=v1_namespace.status.phase if v1_namespace.status else None,
        )
