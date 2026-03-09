"""Project 도메인 Repository 인터페이스"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.kubernetes.namespace import Namespace
from src.core.kubernetes.resource_quota import ResourceQuota
from src.core.kubernetes.service import Service
from src.core.project.model import Project


class ProjectRepository(ABC):
    """
    Project 도메인 Repository.

    Namespace, ResourceQuota, Service 등
    Project 생명주기에 필요한 모든 인프라 연산을 추상화한다.
    """

    # ── Project (Bundle) ─────────────────────────────────────────────────────

    @abstractmethod
    async def save(self, project: Project) -> Project:
        """Project 전체 프로비저닝 (Namespace + ResourceQuota + Harbor Secret + SA, 멱등성 보장)"""

    # ── Namespace ────────────────────────────────────────────────────────────

    @abstractmethod
    async def save_namespace(self, namespace: Namespace) -> Namespace:
        """Namespace 저장 (생성 또는 업데이트, 멱등성 보장)"""

    @abstractmethod
    async def find_namespace(self, id: str) -> Optional[Namespace]:
        """ID로 Namespace 조회"""

    @abstractmethod
    async def delete_namespace(self, id: str) -> bool:
        """Namespace 삭제"""

    @abstractmethod
    async def exists_namespace(self, id: str) -> bool:
        """Namespace 존재 여부 확인"""

    # ── ResourceQuota ────────────────────────────────────────────────────────

    @abstractmethod
    async def save_resource_quota(self, resource_quota: ResourceQuota) -> ResourceQuota:
        """ResourceQuota 저장 (생성 또는 업데이트, 멱등성 보장)"""

    @abstractmethod
    async def find_all_resource_quotas(
        self,
        namespace: str,
        label_selector: Optional[str] = None,
    ) -> List[ResourceQuota]:
        """네임스페이스 내 ResourceQuota 목록 조회"""

    @abstractmethod
    async def exists_resource_quota(self, id: str, namespace: str) -> bool:
        """ResourceQuota 존재 여부 확인"""

    @abstractmethod
    async def delete_resource_quota(self, id: str, namespace: str) -> bool:
        """ResourceQuota 삭제"""

    # ── Service ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def find_service(self, id: str, namespace: str) -> Optional[Service]:
        """ID로 Service 조회"""

    @abstractmethod
    async def save_service(self, service: Service) -> Service:
        """Service 저장 (생성 또는 업데이트, 멱등성 보장)"""

    @abstractmethod
    async def delete_service(self, id: str, namespace: str) -> bool:
        """Service 삭제"""
