from abc import ABC, abstractmethod
from typing import List, Optional

from .model import Pod, PodLogs, Event


class PodRepository(ABC):
    """Pod Repository 추상 인터페이스"""

    @abstractmethod
    async def find_by_deployment(
        self,
        deployment_name: str,
        namespace: str,
    ) -> List[Pod]:
        """Deployment 소속 Pod 목록 조회"""
        ...

    @abstractmethod
    async def get_logs(
        self,
        pod_name: str,
        namespace: str,
        tail_lines: Optional[int] = None,
        since_seconds: Optional[int] = None,
        timestamps: bool = False,
    ) -> Optional[PodLogs]:
        """Pod 로그 조회"""
        ...

    @abstractmethod
    async def get_events_by_deployment(
        self,
        deployment_name: str,
        namespace: str,
    ) -> List[Event]:
        """Deployment 관련 이벤트 조회"""
        ...
