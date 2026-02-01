from typing import List, Dict, Any, Optional

from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException

from src.core.proxmox.cluster_checker import ProxmoxClusterChecker
from src.infra.proxmox.exceptions import (
    ProxmoxClusterNodesException,
    ProxmoxClusterVMsException,
    ProxmoxClusterStorageException,
    ProxmoxClusterResourcesException,
)


class ProxmoxerClusterChecker(ProxmoxClusterChecker):
    """Proxmox 클러스터 리소스 조회 구현체"""

    def __init__(self, api: ProxmoxAPI):
        self._api = api

    async def get_nodes(self) -> List[Dict[str, Any]]:
        """클러스터의 모든 노드 상태 조회"""
        try:
            resources = self._api.cluster.resources.get()
            return [r for r in resources if r.get("type") == "node"]
        except ResourceException as e:
            raise ProxmoxClusterNodesException(
                reason=str(e),
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxClusterNodesException(
                reason=str(e)
            ) from e

    async def get_vms(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """클러스터의 모든 VM 상태 조회 (qemu + lxc)"""
        try:
            resources = self._api.cluster.resources.get()
            vms = [r for r in resources if r.get("type") in ("qemu", "lxc")]
            if node:
                vms = [vm for vm in vms if vm.get("node") == node]
            return vms
        except ResourceException as e:
            raise ProxmoxClusterVMsException(
                reason=str(e),
                node=node,
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxClusterVMsException(
                reason=str(e),
                node=node
            ) from e

    async def get_storage(self, node: str) -> List[Dict[str, Any]]:
        """특정 노드의 스토리지 상태 조회 (/nodes/{node}/storage)"""
        try:
            return self._api.nodes(node).storage.get()
        except ResourceException as e:
            raise ProxmoxClusterStorageException(
                node=node,
                reason=str(e),
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxClusterStorageException(
                node=node,
                reason=str(e)
            ) from e

    async def get_all_resources(self) -> List[Dict[str, Any]]:
        """클러스터의 모든 리소스 조회"""
        try:
            return self._api.cluster.resources.get()
        except ResourceException as e:
            raise ProxmoxClusterResourcesException(
                reason=str(e),
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxClusterResourcesException(
                reason=str(e)
            ) from e
