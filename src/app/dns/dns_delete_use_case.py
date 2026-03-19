"""DNS 레코드 삭제 Use Case

흐름:
  1. dns_id 레이블로 VirtualService 조회 (namespace, subdomain 확인)
  2. Cloudflare CNAME 삭제
  3. VirtualService 삭제
"""

from fastapi import Depends

from src.api.v1.app.dns.schemas.response import DnsDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.app.dns.exceptions import DnsRecordNotFoundException
from src.common.config.cloudflare import CloudflareConfig
from src.core.dns import DnsProvider
from src.dependencies.dns import get_dns_provider, get_tunnel_client
from src.dependencies.kubernetes import get_virtualservice_manager
from src.infra.dns.cloudflare_tunnel_client import CloudflareTunnelClient
from src.infra.kubernetes.managers.virtualservice import IstioVirtualServiceManager

_DNS_ID_LABEL = "madp.io/dns-id"
_DNS_SUBDOMAIN_LABEL = "madp.io/dns-subdomain"


class DnsDeleteUseCase(BaseUseCase):
    """DNS 레코드 삭제 Use Case"""

    def __init__(
        self,
        virtualservice_manager: IstioVirtualServiceManager = Depends(get_virtualservice_manager),
        dns_provider: DnsProvider = Depends(get_dns_provider),
        tunnel_client: CloudflareTunnelClient = Depends(get_tunnel_client),
    ):
        self.virtualservice_manager = virtualservice_manager
        self.dns_provider = dns_provider
        self.tunnel_client = tunnel_client
        self._cf = CloudflareConfig()

    async def __call__(self, dns_id: str) -> DnsDeleteResponse:
        # 1. dns_id 레이블로 VirtualService 조회
        vs = await self.virtualservice_manager.find_by_label(f"{_DNS_ID_LABEL}={dns_id}")
        if not vs:
            raise DnsRecordNotFoundException(dns_id)

        meta = vs["metadata"]
        vs_name = meta["name"]
        namespace = meta["namespace"]
        subdomain = meta["labels"].get(_DNS_SUBDOMAIN_LABEL, "")

        # 2. Cloudflare CNAME 삭제
        await self.dns_provider.delete_subdomain_record(
            project_name=namespace,
            subdomain=subdomain,
        )

        # 3. Tunnel Config ingress 규칙 삭제
        full_domain = f"{subdomain}.{self._cf.base_domain}"
        await self.tunnel_client.remove_ingress_rule(full_domain)

        # 4. VirtualService 삭제
        await self.virtualservice_manager.delete_virtualservice(vs_name, namespace)

        return DnsDeleteResponse(id=dns_id, deleted=True)
