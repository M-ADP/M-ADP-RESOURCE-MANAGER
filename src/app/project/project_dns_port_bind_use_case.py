from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectDnsPortBindRequest
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.dns import get_dns_provider
from src.core.dns.provider import DnsProvider
from src.core.kubernetes.service import Service


class ProjectDnsPortBindUseCase(BaseUseCase):

    def __init__(
            self,
            dns_provider: DnsProvider = Depends(get_dns_provider),
    ):
        self.dns_provider = dns_provider

    async def __call__(
            self,
            project_name: str,
            subdomain: str, # dns-id in path
            payload: ProjectDnsPortBindRequest
    ) -> Service:
        """Project DNS와 Service를 바인딩합니다."""
        
        updated_service = await self.dns_provider.bind_dns_to_service(
            project_name=project_name,
            subdomain=subdomain,
            target_service_name=payload.target_service_name
        )

        return updated_service
