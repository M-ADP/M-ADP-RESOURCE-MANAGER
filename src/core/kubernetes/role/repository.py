from abc import ABC, abstractmethod
from typing import List, Optional

from .model import Role


class RoleRepository(ABC):
    """Role Repository 추상 인터페이스"""

    @abstractmethod
    async def save(self, role: Role) -> Role:
        """Role 저장 (생성 또는 업데이트, 멱등성 보장)"""
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[Role]:
        """이름과 네임스페이스로 Role 조회"""
        ...

    @abstractmethod
    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Role]:
        """Role 목록 조회"""
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """Role 삭제"""
        ...

    @abstractmethod
    async def exists(self, name: str, namespace: str) -> bool:
        """Role 존재 여부 확인"""
        ...
