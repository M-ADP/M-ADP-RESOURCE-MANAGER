from abc import ABC, abstractmethod
from typing import List, Optional

from .model import Secret


class SecretRepository(ABC):
    """Secret Repository 추상 인터페이스

    Note: RMS는 Secret 값을 직접 관리하지 않고,
    Vault 연동을 통한 Secret 접근 구조만 관리합니다.
    """

    @abstractmethod
    async def save(self, secret: Secret) -> Secret:
        """Secret 저장 (생성 또는 업데이트, 멱등성 보장)"""
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[Secret]:
        """이름과 네임스페이스로 Secret 조회"""
        ...

    @abstractmethod
    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Secret]:
        """Secret 목록 조회"""
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """Secret 삭제"""
        ...

    @abstractmethod
    async def exists(self, name: str, namespace: str) -> bool:
        """Secret 존재 여부 확인"""
        ...
