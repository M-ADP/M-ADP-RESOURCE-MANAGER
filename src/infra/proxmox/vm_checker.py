from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException

from src.core.proxmox.vm_checker import ProxmoxVMChecker
from src.infra.proxmox.exceptions import (
    ProxmoxVMListException,
    ProxmoxVMNotFoundException,
    ProxmoxVMStatusException,
    ProxmoxVMMetricsException,
)


class ProxmoxerVMChecker(ProxmoxVMChecker):

    def __init__(self, api: ProxmoxAPI):
        self._api = api

    async def list(self, node: str):
        try:
            return [
                vm["vmid"]
                for vm in self._api.nodes(node).qemu.get()
            ]
        except ResourceException as e:
            raise ProxmoxVMListException(
                node=node,
                reason=str(e),
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxVMListException(
                node=node,
                reason=str(e)
            ) from e

    async def status(self, node: str, vmid: int):
        try:
            return self._api.nodes(node).qemu(vmid).status.current.get()
        except ResourceException as e:
            if getattr(e, "status_code", None) == 404:
                raise ProxmoxVMNotFoundException(
                    node=node,
                    vmid=vmid,
                    detail={"original_error": str(e)}
                ) from e
            raise ProxmoxVMStatusException(
                node=node,
                vmid=vmid,
                reason=str(e),
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxVMStatusException(
                node=node,
                vmid=vmid,
                reason=str(e)
            ) from e

    async def metrics(self, node: str, vmid: int, timeframe: str):
        try:
            return self._api.nodes(node).qemu(vmid).rrddata.get(
                timeframe=timeframe
            )
        except ResourceException as e:
            if getattr(e, "status_code", None) == 404:
                raise ProxmoxVMNotFoundException(
                    node=node,
                    vmid=vmid,
                    detail={"original_error": str(e)}
                ) from e
            raise ProxmoxVMMetricsException(
                node=node,
                vmid=vmid,
                timeframe=timeframe,
                reason=str(e),
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxVMMetricsException(
                node=node,
                vmid=vmid,
                timeframe=timeframe,
                reason=str(e)
            ) from e
