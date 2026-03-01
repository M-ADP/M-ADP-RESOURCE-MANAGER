from abc import ABC, abstractmethod

from src.core.proxmox.cluster_checker import ProxmoxClusterChecker
from src.core.proxmox.node_checker import ProxmoxNodeChecker
from src.core.proxmox.vm_checker import ProxmoxVMChecker


class ProxmoxClient(ABC):

    @abstractmethod
    async def ping(self):
        raise NotImplementedError

    @abstractmethod
    def cluster(self) -> ProxmoxClusterChecker:
        """클러스터 리소스 조회 (권장)"""
        raise NotImplementedError

    @abstractmethod
    def node(self) -> ProxmoxNodeChecker:
        raise NotImplementedError

    @abstractmethod
    def vm(self) -> ProxmoxVMChecker:
        raise NotImplementedError
