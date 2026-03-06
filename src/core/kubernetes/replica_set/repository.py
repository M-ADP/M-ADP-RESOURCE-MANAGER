from abc import ABC, abstractmethod
from typing import List, Optional

from .model import ReplicaSet


class ReplicaSetRepository(ABC):
    """ReplicaSet Repository 추상 인터페이스"""

    @abstractmethod
    async def save(self, replicaset: ReplicaSet) -> ReplicaSet:
        """ReplicaSet 저장 (생성 또는 업데이트, 멱등성 보장)"""
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[ReplicaSet]:
        """이름과 네임스페이스로 ReplicaSet 조회"""
        ...

    @abstractmethod
    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[ReplicaSet]:
        """ReplicaSet 목록 조회"""
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """ReplicaSet 삭제"""
        ...

    @abstractmethod
    async def exists(self, name: str, namespace: str) -> bool:
        """ReplicaSet 존재 여부 확인"""
        ...
