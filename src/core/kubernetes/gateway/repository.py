from abc import ABC, abstractmethod
from typing import List, Optional

from .model import Gateway


class GatewayRepository(ABC):
    """Gateway Repository 추상 인터페이스"""

    @abstractmethod
    async def save(self, gateway: Gateway) -> Gateway:
        """
        Gateway 저장 (생성 또는 업데이트, 멱등성 보장)

        Args:
            gateway: 저장할 Gateway 도메인 객체

        Returns:
            저장된 Gateway 도메인 객체
        """
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[Gateway]:
        """
        이름과 네임스페이스로 Gateway 조회

        Args:
            name: Gateway 이름
            namespace: 네임스페이스

        Returns:
            Gateway 도메인 객체, 없으면 None
        """
        ...

    @abstractmethod
    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Gateway]:
        """
        Gateway 목록 조회

        Args:
            namespace: 네임스페이스 (None이면 전체)
            label_selector: 레이블 셀렉터

        Returns:
            Gateway 도메인 객체 목록
        """
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """
        Gateway 삭제

        Args:
            name: Gateway 이름
            namespace: 네임스페이스

        Returns:
            삭제 성공 여부
        """
        ...

    @abstractmethod
    async def exists(self, name: str, namespace: str) -> bool:
        """
        Gateway 존재 여부 확인

        Args:
            name: Gateway 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        ...
