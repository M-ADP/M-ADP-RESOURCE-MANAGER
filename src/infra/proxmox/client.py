from proxmoxer import ProxmoxAPI

from src.core.proxmox.client import ProxmoxClient
from src.core.proxmox.node_checker import ProxmoxNodeChecker
from src.core.proxmox.vm_checker import ProxmoxVMChecker


class ProxmoxClientImpl(ProxmoxClient):

    def __init__(self, api: ProxmoxAPI):
        self._api = api

    async def ping(self) -> bool:
        try:
            self._api.version.get()
            return True
        except Exception:
            return False

    def node(self) -> ProxmoxNodeChecker:
        return ProxmoxerNodeChecker(self._api)

    def vm(self) -> ProxmoxVMChecker:
        return ProxmoxerVMChecker(self._api)