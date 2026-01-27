from abc import abstractmethod
from typing import List, Dict, Any


class ProxmoxNodeChecker:

    @abstractmethod
    async def list(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    async def status(self, node: str) -> Dict[str, Any]:
        raise NotImplementedError