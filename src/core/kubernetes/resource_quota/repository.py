from abc import ABC, abstractmethod

from src.core.kubernetes.resource_quota.model import ResourceQuotaLimits


class ResourceQuotaRepository(ABC):

    @abstractmethod
    async def delete_resource_quota(
            self,
            resource_quota : ResourceQuotaLimits
    ):
        raise NotImplementedError