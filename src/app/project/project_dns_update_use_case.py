from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectDnsUpdateRequest
from src.app.base_use_case import BaseUseCase
from src.dependencies.dns import get_dns_provider
from src.core.dns import DnsProvider, DnsRecord


class ProjectDnsUpdateUseCase(BaseUseCase):

    def __init__(
            self,
            dns_provider: DnsProvider = Depends(get_dns_provider),
    ):
        self.dns_provider = dns_provider

    async def __call__(
            self,
            project_id: str,
            old_subdomain: str,
            payload: ProjectDnsUpdateRequest
    ) -> DnsRecord:
        """Project DNS 수정"""

        dns_record = await self.dns_provider.update_subdomain_record(
            project_name=f"project-{project_id}",
            old_subdomain=old_subdomain,
            new_subdomain=payload.new_subdomain
        )

        return dns_record
