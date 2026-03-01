"""HPA Repository 인터페이스"""

from abc import ABC, abstractmethod
from typing import Optional, List

from .model import HorizontalPodAutoscaler


class HpaRepository(ABC):
    """HPA Repository 추상 인터페이스"""

    @abstractmethod
    async def save(self, hpa: HorizontalPodAutoscaler) -> HorizontalPodAutoscaler:
        """HPA 저장 (생성 또는 업데이트)"""
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[HorizontalPodAutoscaler]:
        """이름으로 HPA 조회"""
        ...

    @abstractmethod
    async def find_all(self, namespace: str) -> List[HorizontalPodAutoscaler]:
        """네임스페이스 내의 모든 HPA 조회"""
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """HPA 삭제"""
        ...
