from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ProxmoxVMChecker(ABC):

    @abstractmethod
    async def list(self, node: str) -> List[int]:
        raise NotImplementedError

    @abstractmethod
    async def status(self, node: str, vmid: int) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def metrics(self, node: str, vmid: int, timeframe: str) -> Dict[str, Any]:
        raise NotImplementedError