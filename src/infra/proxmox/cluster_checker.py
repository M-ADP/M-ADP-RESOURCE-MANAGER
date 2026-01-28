from typing import List, Dict, Any, Optional

from proxmoxer import ProxmoxAPI

from src.core.proxmox.cluster_checker import ProxmoxClusterChecker


class ProxmoxerClusterChecker(ProxmoxClusterChecker):
    """Proxmox 클러스터 리소스 조회 구현체"""

    def __init__(self, api: ProxmoxAPI):
        self._api = api

    async def get_nodes(self) -> List[Dict[str, Any]]:
        """클러스터의 모든 노드 상태 조회"""
        resources = self._api.cluster.resources.get()
        return [r for r in resources if r.get("type") == "node"]

    async def get_vms(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """클러스터의 모든 VM 상태 조회 (qemu + lxc)"""
        resources = self._api.cluster.resources.get()
        vms = [r for r in resources if r.get("type") in ("qemu", "lxc")]
        if node:
            vms = [vm for vm in vms if vm.get("node") == node]
        return vms

    async def get_storage(self, node: str) -> List[Dict[str, Any]]:
        """특정 노드의 스토리지 상태 조회 (/nodes/{node}/storage)"""
        return self._api.nodes(node).storage.get()

    async def get_all_resources(self) -> List[Dict[str, Any]]:
        """클러스터의 모든 리소스 조회"""
        return self._api.cluster.resources.get()
