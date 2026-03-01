from proxmoxer import ProxmoxAPI

from src.core.proxmox.client import ProxmoxClient
from src.core.proxmox.cluster_checker import ProxmoxClusterChecker
from src.core.proxmox.node_checker import ProxmoxNodeChecker
from src.core.proxmox.vm_checker import ProxmoxVMChecker
from src.infra.proxmox.cluster_checker import ProxmoxerClusterChecker
from src.infra.proxmox.node_checker import ProxmoxerNodeChecker
from src.infra.proxmox.vm_checker import ProxmoxerVMChecker


class ProxmoxClientImpl(ProxmoxClient):

    def __init__(self, api: ProxmoxAPI):
        self._api = api

    async def ping(self) -> bool:
        try:
            self._api.version.get()
            return True
        except Exception:
            return False

    def cluster(self) -> ProxmoxClusterChecker:
        return ProxmoxerClusterChecker(self._api)

    def node(self) -> ProxmoxNodeChecker:
        return ProxmoxerNodeChecker(self._api)

    def vm(self) -> ProxmoxVMChecker:
        return ProxmoxerVMChecker(self._api)
