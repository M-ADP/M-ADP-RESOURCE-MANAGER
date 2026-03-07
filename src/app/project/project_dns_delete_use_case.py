from fastapi import Depends

from src.app.base_use_case import BaseUseCase
from src.dependencies.dns import get_dns_provider
from src.core.dns import DnsProvider


class ProjectDnsDeleteUseCase(BaseUseCase):

    def __init__(
            self,
            dns_provider: DnsProvider = Depends(get_dns_provider),
    ):
        self.dns_provider = dns_provider

    async def __call__(
            self,
            project_name: str,
            subdomain: str
    ) -> bool:
        """Project DNS 삭제"""
        
        deleted = await self.dns_provider.delete_subdomain_record(
            project_name=f"project-{project_name}",
            subdomain=subdomain
        )

        return deleted
