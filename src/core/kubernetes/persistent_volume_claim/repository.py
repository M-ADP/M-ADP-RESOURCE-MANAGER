from abc import ABC, abstractmethod
from typing import List, Optional

from .model import PersistentVolumeClaim


class PersistentVolumeClaimRepository(ABC):
    """PersistentVolumeClaim Repository 추상 인터페이스"""

    @abstractmethod
    async def save(self, pvc: PersistentVolumeClaim) -> PersistentVolumeClaim:
        """PVC 저장 (생성 또는 업데이트, 멱등성 보장)"""
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[PersistentVolumeClaim]:
        """이름과 네임스페이스로 PVC 조회"""
        ...

    @abstractmethod
    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[PersistentVolumeClaim]:
        """PVC 목록 조회"""
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """PVC 삭제"""
        ...

    @abstractmethod
    async def exists(self, name: str, namespace: str) -> bool:
        """PVC 존재 여부 확인"""
        ...

    @abstractmethod
    async def resize(self, name: str, namespace: str, new_storage: str) -> PersistentVolumeClaim:
        """PVC 스토리지 크기 변경 (증가만 가능)"""
        ...
