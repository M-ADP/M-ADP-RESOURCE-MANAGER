from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException

from src.core.proxmox.node_checker import ProxmoxNodeChecker
from src.infra.proxmox.exceptions import (
    ProxmoxNodeListException,
    ProxmoxNodeNotFoundException,
    ProxmoxNodeStatusException,
)


class ProxmoxerNodeChecker(ProxmoxNodeChecker):

    def __init__(self, api: ProxmoxAPI):
        self._api = api

    async def list(self):
        try:
            return [n["node"] for n in self._api.nodes.get()]
        except ResourceException as e:
            raise ProxmoxNodeListException(
                reason=str(e),
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxNodeListException(
                reason=str(e)
            ) from e

    async def status(self, node: str):
        try:
            return self._api.nodes(node).status.get()
        except ResourceException as e:
            if getattr(e, "status_code", None) == 404:
                raise ProxmoxNodeNotFoundException(
                    node=node,
                    detail={"original_error": str(e)}
                ) from e
            raise ProxmoxNodeStatusException(
                node=node,
                reason=str(e),
                detail={"status_code": getattr(e, "status_code", None)}
            ) from e
        except Exception as e:
            raise ProxmoxNodeStatusException(
                node=node,
                reason=str(e)
            ) from e
