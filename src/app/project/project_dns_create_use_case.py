from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.project.schmas.request import ProjectDnsCreateRequest
from src.app.base_use_case import BaseUseCase
from src.dependencies.dns import get_dns_provider
from src.core.dns import DnsProvider, DnsRecord


class ProjectDnsCreateUseCase(BaseUseCase):

    def __init__(
            self,
            dns_provider: DnsProvider = Depends(get_dns_provider),
    ):
        self.dns_provider = dns_provider

    async def __call__(
            self,
            project_id: str,
            payload: ProjectDnsCreateRequest
    ) -> DnsRecord:
        """Project DNS 생성"""

        dns_record = await self.dns_provider.create_subdomain_record(
            project_name=ProjectId(project_id).namespace,
            subdomain=payload.subdomain
        )

        return dns_record
