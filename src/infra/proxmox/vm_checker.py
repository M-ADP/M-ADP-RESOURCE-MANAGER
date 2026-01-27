from proxmoxer import ProxmoxAPI

from src.core.proxmox.vm_checker import ProxmoxVMChecker


class ProxmoxerVMChecker(ProxmoxVMChecker):

    def __init__(self, api: ProxmoxAPI):
        self._api = api

    async def list(self, node: str):
        return [
            vm["vmid"]
            for vm in self._api.nodes(node).qemu.get()
        ]

    async def status(self, node: str, vmid: int):
        return self._api.nodes(node).qemu(vmid).status.current.get()

    async def metrics(self, node: str, vmid: int, timeframe: str):
        return self._api.nodes(node).qemu(vmid).rrddata.get(
            timeframe=timeframe
        )
