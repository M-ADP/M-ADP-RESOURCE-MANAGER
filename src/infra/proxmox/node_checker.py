from proxmoxer import ProxmoxAPI

from src.core.proxmox.node_checker import ProxmoxNodeChecker

class ProxmoxerNodeChecker(ProxmoxNodeChecker):

    def __init__(self, api: ProxmoxAPI):
        self._api = api

    async def list(self):
        return [n["node"] for n in self._api.nodes.get()]

    async def status(self, node: str):
        return self._api.nodes(node).status.get()
