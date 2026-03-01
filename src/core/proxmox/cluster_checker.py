from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ProxmoxClusterChecker(ABC):
    """Proxmox 클러스터 리소스 조회 추상 클래스"""

    @abstractmethod
    async def get_nodes(self) -> List[Dict[str, Any]]:
        """클러스터의 모든 노드 상태 조회 (/cluster/resources?type=node)"""
        raise NotImplementedError

    @abstractmethod
    async def get_vms(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """클러스터의 모든 VM 상태 조회 (/cluster/resources?type=vm)"""
        raise NotImplementedError

    @abstractmethod
    async def get_storage(self, node: str) -> List[Dict[str, Any]]:
        """특정 노드의 스토리지 상태 조회 (/nodes/{node}/storage)"""
        raise NotImplementedError

    @abstractmethod
    async def get_all_resources(self) -> List[Dict[str, Any]]:
        """클러스터의 모든 리소스 조회 (/cluster/resources)"""
        raise NotImplementedError
