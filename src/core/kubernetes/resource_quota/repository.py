from abc import ABC, abstractmethod
from typing import List, Optional

from .model import ResourceQuota


class ResourceQuotaRepository(ABC):
    """ResourceQuota Repository 추상 인터페이스"""

    @abstractmethod
    async def save(self, resource_quota: ResourceQuota) -> ResourceQuota:
        """
        ResourceQuota 저장 (생성 또는 업데이트, 멱등성 보장)

        Args:
            resource_quota: 저장할 ResourceQuota 도메인 객체

        Returns:
            저장된 ResourceQuota 도메인 객체
        """
        ...

    @abstractmethod
    async def find_by_name(self, name: str, namespace: str) -> Optional[ResourceQuota]:
        """
        이름과 네임스페이스로 ResourceQuota 조회

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스

        Returns:
            ResourceQuota 도메인 객체, 없으면 None
        """
        ...

    @abstractmethod
    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[ResourceQuota]:
        """
        ResourceQuota 목록 조회

        Args:
            namespace: 네임스페이스 (None이면 전체)
            label_selector: 레이블 셀렉터

        Returns:
            ResourceQuota 도메인 객체 목록
        """
        ...

    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        """
        ResourceQuota 삭제

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스

        Returns:
            삭제 성공 여부
        """
        ...

    @abstractmethod
    async def exists(self, name: str, namespace: str) -> bool:
        """
        ResourceQuota 존재 여부 확인

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        ...
