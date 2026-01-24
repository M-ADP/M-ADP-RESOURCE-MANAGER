from abc import ABC, abstractmethod
from typing import List, Optional

from .model import ConfigMap


class ConfigMapRepository(ABC):
    """ConfigMap Repository 추상 인터페이스"""

    @abstractmethod
    async def save(self, configmap: ConfigMap) -> ConfigMap:
        """ConfigMap 저장 (생성 또는 업데이트, 멱등성 보장)"""
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[ConfigMap]:
        """이름과 네임스페이스로 ConfigMap 조회"""
        ...

    @abstractmethod
    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[ConfigMap]:
        """ConfigMap 목록 조회"""
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """ConfigMap 삭제"""
        ...

    @abstractmethod
    async def exists(self, name: str, namespace: str) -> bool:
        """ConfigMap 존재 여부 확인"""
        ...
