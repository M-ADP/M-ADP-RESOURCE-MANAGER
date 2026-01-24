from abc import ABC, abstractmethod
from typing import Optional, List
from .model import VerticalPodAutoscaler


class VpaRepository(ABC):
    """VPA Repository 추상 인터페이스"""

    @abstractmethod
    async def save(self, vpa: VerticalPodAutoscaler) -> VerticalPodAutoscaler:
        """VPA 저장 (생성 또는 업데이트)"""
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[VerticalPodAutoscaler]:
        """이름으로 VPA 조회"""
        ...

    @abstractmethod
    async def find_all(self, namespace: str) -> List[VerticalPodAutoscaler]:
        """네임스페이스 내의 모든 VPA 조회"""
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """VPA 삭제"""
        ...
